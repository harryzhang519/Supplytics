from flask import Blueprint, jsonify, request
from modules.finviz_scraper import scrape_finviz_news
from modules.ingestion import ingest_signal
from modules.classifier import classifier as high_speed_classifier
from modules.orchestrator import analyze_disruption
from services.firestore_factory import firestore_db
import logging
import time
import threading

cron_bp = Blueprint('cron', __name__)
logger = logging.getLogger(__name__)

import math
import re

def _cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def _jaccard_similarity(text1, text2):
    """Fallback text similarity for realistic local simulation."""
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))
    if not words1 or not words2:
        return 0.0
    return len(words1.intersection(words2)) / len(words1.union(words2))

# ── In-memory store for currently processing signals ─────────────────
# We still use these during the active scrape loop, but they are pushed 
# to Firestore at the end of the run.
_processed_headlines = set()   
_processed_urls = set()        
_processed_embeddings = []     

# Severe threshold: signals at or above this run through the full orchestrator
AUTO_ANALYZE_THRESHOLD = 6
CACHE_COLLECTION = "system_cache"
CACHE_DOC_ID = "cron_news_cache"
CACHE_TTL_SECONDS = 30 * 60  # 30 minutes


def _run_async_analysis(text, classification):
    """Heavy AI orchestration runs in a background thread to keep UI responsive."""
    try:
        logger.info(f"   🚨 [Async] Starting deep analysis: {text[:60]}...")
        result = analyze_disruption(text)
        result["source"] = "finviz-auto"
        result["scraped_headline"] = text
        
        # Pull existing cache to append this disruption
        cache = firestore_db.get_document(CACHE_COLLECTION, CACHE_DOC_ID) or {}
        auto_disruptions = cache.get("auto_disruptions", [])
        
        auto_disruptions.append(result)
        if len(auto_disruptions) > 30:
            auto_disruptions = auto_disruptions[-30:]
            
        firestore_db.update_document(CACHE_COLLECTION, CACHE_DOC_ID, {
            "auto_disruptions": auto_disruptions
        })
        
        logger.info(f"   ✅ [Async] Analysis complete: ${result['strategy']['revenue_at_risk']:,} at risk")
    except Exception as e:
        logger.error(f"   ❌ [Async] Orchestrator failed for '{text[:40]}': {e}")
        # Optionally remove from _processed_headlines on failure to allow retry
        # _processed_headlines.discard(text)


@cron_bp.route('/scrape-finviz', methods=['POST', 'GET'])
def cron_scrape_finviz():
    """
    Cron endpoint triggered by Scheduler.
    Checks TTL cache first to prevent redundant scrapes across serverless instances.
    """
    force_refresh = request.args.get('force', 'false').lower() == 'true'
    
    # 0. Check TTL Cache
    cache = firestore_db.get_document(CACHE_COLLECTION, CACHE_DOC_ID)
    current_time = time.time()
    
    if cache and not force_refresh:
        last_scraped = cache.get("last_scraped_time", 0)
        if (current_time - last_scraped) < CACHE_TTL_SECONDS:
            logger.info("Cron: Finviz cache is still fresh. Skipping scrape.")
            return jsonify({
                "status": "success",
                "cached": True,
                "message": "Returned from cache to save API limits."
            }), 200

    logger.info("Cron triggered: /api/cron/scrape-finviz executing fresh scrape...")
    
    headlines = scrape_finviz_news()
    
    # 1. Handle Scraper Failures (Rate limiting, connection issues, etc.)
    if headlines is None:
        return jsonify({
            "status": "error",
            "message": "The news scraper is currently unavailable (potential rate limiting or connectivity issue). Check backend logs for status codes."
        }), 503

    # 2. Handle Case: Scraper worked, but no Bloomberg headlines found
    if not headlines:
        return jsonify({
            "status": "success", 
            "message": "No new Bloomberg headlines found at this time.",
            "scraped_total": 0,
            "processed": 0,
            "auto_analyzed_started": 0
        }), 200
        
    headlines_to_process = headlines[:10]
    classified_signals = []
    threads_started = 0
    
    for item in headlines_to_process:
        text = item["text"]
        url = item["url"]
        try:
            # 1. Deduplicate by exact Article URL (The safest block against Finviz syndication / updates)
            if url in _processed_urls:
                continue
            
            # 2. Global exact-match deduplication
            if text in _processed_headlines:
                continue
                
            # 3. Semantic deduplication
            from config import USE_REAL_VERTEX
            is_semantic_duplicate = False
            
            if USE_REAL_VERTEX:
                from services.vertex_simulator import vertex_ai
                new_embedding = vertex_ai.generate_embedding(text)
                
                for pe in _processed_embeddings:
                    sim = _cosine_similarity(new_embedding, pe['embedding'])
                    if sim > 0.65:
                        is_semantic_duplicate = True
                        logger.info(f"Skipping semantic duplicate: '{text[:40]}' matches '{pe['text'][:40]}' (sim: {sim:.2f})")
                        break
                        
                if not is_semantic_duplicate:
                    _processed_embeddings.append({'text': text, 'embedding': new_embedding})
                    if len(_processed_embeddings) > 100:
                        _processed_embeddings.pop(0)
            else:
                # Simulator fallback: Hash embeddings are zero-collision, so cosine sim fails. Use Jaccard Words.
                for past_text in _processed_headlines:
                    sim = _jaccard_similarity(text, past_text)
                    if sim > 0.4: # Jaccard > 0.4 implies significant overlap in short news headlines
                        is_semantic_duplicate = True
                        logger.info(f"Skipping jaccard duplicate: '{text[:40]}' matches '{past_text[:40]}' (sim: {sim:.2f})")
                        break

            if is_semantic_duplicate:
                _processed_headlines.add(text) # Add to exact match for faster rejection next time
                _processed_urls.add(url)
                continue

            # Log clean, unique signals
            _processed_headlines.add(text)
            _processed_urls.add(url)
            
            # Memory management for exact text match
            if len(_processed_headlines) > 500:
                _processed_headlines.pop()
            if len(_processed_urls) > 500:
                _processed_urls.pop()

            classification = high_speed_classifier.classify(text)
            
            signal_entry = {
                "text": text,
                "url": url,
                "category": classification.get("category", "general"),
                "severity": classification.get("severity", 1),
                "region": classification.get("region"),
                "reasoning": classification.get("reasoning", ""),
                "keywords": classification.get("keywords", []),
                "classifier": classification.get("classifier", "keyword-fallback"),
                "timestamp": time.time(),
                "source": "finviz",
            }
            classified_signals.append(signal_entry)
            
            # High-severity signals trigger background analysis
            if classification.get("severity", 0) >= AUTO_ANALYZE_THRESHOLD and classification.get("category") != "general":
                # Ingest immediately so it shows up in "Recent Signals" instantly
                ingest_signal(text, signal_type="news", pre_classified=classification)
                
                thread = threading.Thread(target=_run_async_analysis, args=(text, classification))
                thread.daemon = True
                thread.start()
                threads_started += 1
            else:
                # Still ingest for context
                ingest_signal(text, signal_type="news", pre_classified=classification)

        except Exception as e:
            logger.error(f"Error processing headline '{text[:40]}': {e}")
            continue
    
    cache = firestore_db.get_document(CACHE_COLLECTION, CACHE_DOC_ID) or {}
    scraped_signals = cache.get("scraped_signals", [])
    
    scraped_signals.extend(classified_signals)
    if len(scraped_signals) > 100:
        scraped_signals = scraped_signals[-100:]
        
    # Update cache
    firestore_db.add_document(CACHE_COLLECTION, {
        "last_scraped_time": current_time,
        "scraped_signals": scraped_signals,
        "auto_disruptions": cache.get("auto_disruptions", [])
    }, doc_id=CACHE_DOC_ID)
    
    return jsonify({
        "status": "success",
        "cached": False,
        "scraped_total": len(headlines),
        "processed": len(headlines_to_process),
        "auto_analyzed_started": threads_started,
        "message": "Scrape complete. Analysis continuing in background." if threads_started > 0 else "Scrape complete."
    })


@cron_bp.route('/scraped-signals', methods=['GET'])
def get_scraped_signals():
    """Return all recently scraped + classified signals from Firestore cache."""
    cache = firestore_db.get_document(CACHE_COLLECTION, CACHE_DOC_ID) or {}
    signals = cache.get("scraped_signals", [])
    return jsonify({
        "signals": signals[-50:],  # Last 50
        "total": len(signals),
    })


@cron_bp.route('/auto-disruptions', methods=['GET'])
def get_auto_disruptions():
    """Return auto-analyzed disruptions from Firestore cache."""
    cache = firestore_db.get_document(CACHE_COLLECTION, CACHE_DOC_ID) or {}
    disruptions = cache.get("auto_disruptions", [])
    return jsonify({
        "disruptions": disruptions[-10:],  # Last 10
        "total": len(disruptions),
    })
