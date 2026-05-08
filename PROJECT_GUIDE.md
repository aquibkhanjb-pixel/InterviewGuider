# Interview Intelligence System — Project Guide

---

## 1. Problem Statement

Preparing for a technical interview at a specific company is difficult because the information is scattered. Someone interviewing at Amazon has to manually browse through dozens of blog posts on GeeksForGeeks, Reddit threads, Glassdoor reviews, and LeetCode discussions just to get a rough idea of what topics actually come up. There is no structured, data-driven answer to the question: **"What should I study to crack a Google or Amazon interview?"**

The gaps this creates:
- Candidates study generic topics instead of company-specific patterns
- No way to know whether a topic (like Dynamic Programming) is genuinely common at a company or just shows up in one or two posts
- No signal on recency — interview patterns from 3 years ago may not reflect current rounds
- No aggregation across platforms — insights are siloed per website

---

## 2. Solution

**Interview Intelligence System** is a full-stack ML-powered web application that automatically scrapes interview experiences from multiple platforms, extracts technical topics from the raw text using NLP, scores and ranks those topics using consistency scoring and semantic similarity, and presents actionable study insights through a React dashboard.

A user selects a company, clicks "Run Analysis", and within 1-2 minutes gets:
- A ranked list of topics that actually appear in that company's interviews
- A confidence score per topic (how certain we are it matters)
- A consistency score per topic (does this topic appear in most interviews or just a few?)
- A study plan with priority levels and recommended resources

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│  CompanySelector → InsightsChart → StudyPlan → ExperiencesList │
│  MUI components │ Chart.js bars │ Priority badges           │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API calls
┌────────────────────────▼────────────────────────────────────┐
│                     FLASK REST API                           │
│  /api/analysis/<company>   → triggers pipeline job          │
│  /api/jobs/<job_id>        → polls job status               │
│  /api/insights/<company>   → returns ML-scored insights     │
└──────┬───────────────────────────────┬───────────────────────┘
       │                               │
┌──────▼────────────┐       ┌──────────▼───────────────────────┐
│  PIPELINE MANAGER │       │      INSIGHTS GENERATOR           │
│                   │       │                                   │
│  6 Scrapers run   │       │  1. topic_extractor per exp       │
│  concurrently:    │       │  2. consistency_rerank (df/N)     │
│  - GeeksForGeeks  │       │  3. SemanticConfidenceScorer      │
│  - InterviewBit   │       │     (fastembed ONNX, ~50MB RAM)  │
│  - AmbitionBox    │       │  4. Aggregate → priority + recs   │
│  - LeetCode       │       │                                   │
│  - Reddit         │       └──────────────────────────────────┘
│  - Glassdoor      │
└──────┬────────────┘
       │ stores raw experiences
┌──────▼────────────────────────────────────────────────────────┐
│                   PostgreSQL DATABASE                          │
│  companies | interview_experiences | topics | topic_mentions  │
└───────────────────────────────────────────────────────────────┘
```

### Component breakdown

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 18 + MUI + Chart.js | Dashboard, charts, study plan |
| API | Flask 3.0 + Flask-CORS | REST endpoints, job queue |
| Scraping | requests + BeautifulSoup | Raw experience collection |
| NLP | NLTK + keyword dictionary | Topic extraction from text |
| ML Scoring | fastembed (ONNX) + scikit-learn | Semantic confidence + consistency scoring |
| Database | PostgreSQL + SQLAlchemy 2.0 | Persistent storage |
| Deployment | Render (backend) + Vercel (frontend) | Cloud hosting |

### Data flow (step by step)

1. User selects a company and clicks **Run Analysis**
2. Frontend calls `POST /api/analysis/<company>` → returns a `job_id`
3. Flask starts a background thread running `PipelineManager.run_complete_analysis()`
4. Pipeline Manager fires all 6 scrapers. Each scraper discovers URL links for the company, then fetches and parses each experience page
5. Raw experiences are stored in `interview_experiences` table with deduplication on `source_url`
6. `AdvancedTopicExtractor` runs on each experience: matches keywords from a hierarchical dictionary (data structures → array, linked list… | algorithms → DP, sorting…), applies time-weighting (recent = higher weight), computes per-topic confidence
7. `SemanticConfidenceScorer` embeds each topic phrase and surrounding context windows using `fastembed` (ONNX Runtime), computes cosine similarity as a confirmation signal — only for top 5 topics per experience to keep latency low
8. Frontend polls `GET /api/jobs/<job_id>` every 6 seconds until status = `completed`
9. User visits insights → Frontend calls `GET /api/insights/<company>`
10. `CompanyInsightsGenerator` reads all stored experiences, runs `consistency_rerank()` to compute how reliably each topic appears (df / n_experiences), sorts topics by a blended rank (60% frequency + 40% consistency), returns the full payload
11. Dashboard renders the topic chart, study plan with consistency badges, and raw experiences list

---

## 4. How to Explain the Workflow to an Interviewer

> Speak this naturally, not word-for-word. Think of it as telling a story.

---

**Start with the problem (30 seconds)**

> "The motivation was pretty simple — I was preparing for interviews myself and realised there was no good way to know which topics a specific company actually tests. You end up reading random blog posts and guessing. So I built a system that does that research automatically."

---

**Explain what it does at a high level (1 minute)**

> "You type in a company name — say Amazon — and the system scrapes interview experiences from six platforms: GeeksForGeeks, InterviewBit, Reddit, LeetCode, AmbitionBox, and Glassdoor. It parses the text of each experience, identifies which technical topics came up — things like Dynamic Programming, Trees, System Design — and then ranks them by how frequently and confidently they appear. The output is a study plan that tells you: focus on these five topics first, these three are secondary."

---

**Walk through the technical pipeline (2 minutes)**

> "On the backend, I have a Pipeline Manager that fires all six scrapers concurrently using Python's ThreadPoolExecutor. Each scraper finds experience links for the company and then fetches the actual post content.
>
> The interesting part is the NLP layer. I built a keyword dictionary organised by category — data structures, algorithms, system design, programming concepts. For every experience, the Topic Extractor scans the text and counts how many times each topic's keywords appear, applies a time-weight so recent experiences matter more, and produces a confidence score.
>
> On top of that, I added a semantic layer using fastembed. It's a library that runs embedding models via ONNX Runtime instead of PyTorch — I specifically chose it because PyTorch adds 200MB of RAM overhead and my deployment is on Render's free tier which has a 512MB limit. fastembed gives me the same quality embeddings at about 50MB total. For each topic keyword match in the text, I extract a 300-character window around it and compute cosine similarity between that context window and a topic description like 'interview question about dynamic programming'. This tells me whether the keyword is being used meaningfully, not just mentioned in passing.
>
> Then I apply consistency re-ranking. For each topic I compute df divided by N — the fraction of experiences where that topic appears. A topic appearing in every Amazon experience gets consistency 1.0, which is the strongest possible signal to study it. I blend frequency rank and consistency rank 60/40, so both signals reinforce each other. I deliberately avoided IDF here because IDF penalises topics that appear in all experiences — which is exactly backwards for a within-company analysis. IDF makes sense cross-company, to separate what's uniquely Amazon from what every company asks, but not within one company's corpus."

---

**Talk about the frontend (30 seconds)**

> "The frontend is React with Material UI. The main view is a bar chart with two modes — frequency view and consistency view — so you can see both how often a topic comes up and how reliably it appears across interviews. The study plan shows each topic with two badges: a Consistency badge and an AI Confidence badge from the semantic model."

---

**End with results or learnings (30 seconds)**

> "The biggest technical challenge was making the NLP robust on noisy scraped text — interview posts are very informal. I had to build out a large stopword list and context-window extraction to avoid false positives. Another challenge was the scoring design — I initially used IDF re-ranking which actively penalised topics that appear in all experiences. But within a single company's corpus, high document frequency IS the signal — if Arrays appear in 9 out of 9 Amazon experiences, that's the strongest possible reason to study them. I switched to a consistency score that reinforces high-frequency topics instead of demoting them."

---

## 5. Top 10 Interview Questions and Answers

---

### Q1. Why did you choose scraping over using official APIs?

**Answer:**
Most of these platforms — GeeksForGeeks, InterviewBit, AmbitionBox — do not offer public APIs for their community content. Reddit does have an API but the interview experience data lives in informal posts, not a structured endpoint. Scraping was the only practical way to access the data. I handled it responsibly: I implemented rate limiting, respected `robots.txt` where applicable, and deduplication via `source_url` to avoid hammering the same page twice.

---

### Q2. Why did you not use TF-IDF for ranking, and what did you use instead?

**Answer:**
TF-IDF uses IDF = log(N/df) to penalise topics that appear in many documents. In cross-document retrieval that makes sense — a word in every document carries no discriminative information. But this system analyses a single company's corpus. If Dynamic Programming appears in all 25 Amazon experiences, that high document frequency is exactly the signal the user needs — it means Amazon reliably tests DP. Applying IDF would score it at log(25/25) = 0 and bury it, which is the opposite of useful.

So instead I use a consistency score: df / N, the fraction of experiences where the topic appears. A topic present in every experience gets consistency 1.0 — highest priority. A topic appearing in only 2 experiences gets 0.08 — treat with caution. The final sort blends 60% frequency rank with 40% consistency rank, so both signals reinforce each other.

IDF remains the right tool at the cross-company level — when you want to distinguish what's uniquely Amazon from what every company tests. That's noted as a future improvement once multi-company data is collected.

---

### Q3. What is semantic confidence scoring and why did you add it?

**Answer:**
Keyword matching has a core weakness: it counts every mention of a keyword equally. If someone says "we did NOT do dynamic programming" or just mentions "DP" in passing, the keyword counter increments. Semantic confidence addresses this by using `fastembed` to embed a 300-character window of text around each keyword match and compare it via cosine similarity to a description of the topic. If the context window is semantically close to "interview question about dynamic programming", the score is high. If it's a casual mention, the score is low. This acts as a quality filter on top of keyword frequency.

I specifically chose `fastembed` over `sentence-transformers` because fastembed runs models via ONNX Runtime rather than PyTorch. PyTorch adds ~200MB of RAM overhead at import time — on Render's free tier with a 512MB limit that caused OOM crashes. fastembed delivers the same quality at ~50MB total, which is a deliberate engineering trade-off I made for the deployment constraint.

---

### Q4. How do you handle duplicate experiences across platforms?

**Answer:**
Each experience is stored with a `source_url` field that has a unique constraint in the database. Before inserting, the scraper checks if that URL already exists. If it does, it skips the record. This prevents the same post from inflating topic counts just because it was indexed by multiple scrapers or re-discovered in a subsequent run.

---

### Q5. How does the background job system work?

**Answer:**
When the user clicks "Run Analysis", the frontend calls a Flask endpoint that starts a background thread and immediately returns a `job_id`. The pipeline runs asynchronously in that thread — scraping can take 60-120 seconds. The frontend polls `GET /api/jobs/<job_id>` every 6 seconds. The job object is stored in an in-memory dictionary with a status field (`queued → running → completed/failed`). When the pipeline finishes, the job status is updated and the next poll from the frontend picks it up. I chose in-memory storage over a proper queue like Celery deliberately, to keep the deployment simple — the trade-off is that jobs are lost on server restart, which is acceptable for this use case.

---

### Q6. How do you weight recent experiences more than older ones?

**Answer:**
Each experience gets a `time_weight` computed at scrape time based on how many days ago it was published. Experiences from the last 30 days get weight 1.0. Older experiences decay: weight = max(0.3, 1.0 - (days / 365) * 0.7). This cap at 0.3 ensures old experiences still contribute but with less influence. The `weighted_frequency` field used in scoring is the sum of these time-weights across experiences where a topic appears, not just a raw count. This way, a topic that dominated interviews this month outranks one that was popular two years ago even if the older one has more total mentions.

---

### Q7. What happens when there is not enough data for a company?

**Answer:**
The system has a minimum threshold of 3 experiences. If fewer than 3 are collected, `generate_comprehensive_insights()` returns a status of `insufficient_data` with a message explaining why. The API translates this into a user-facing message and returns a 200 (not a 500) with an empty insights object. The frontend shows an alert with guidance to run analysis again or try a more popular company. I chose 3 as the threshold because below that you cannot compute meaningful frequency statistics — a single experience could be an outlier.

---

### Q8. How does the system scale if I want to add a new company or a new scraper?

**Answer:**
Adding a new company requires no code changes — companies are dynamic, stored in the database on first scrape. Adding a new scraper requires writing a class that extends `BaseScraper` and implementing two methods: `discover_experience_urls(company_name)` and `extract_experience_data(url)`. The `PipelineManager` accepts the scrapers dict in its constructor, so you register it there. The rest of the pipeline — storage, topic extraction, insights generation — is completely scraper-agnostic. This separation of concerns was intentional so the system can grow without touching the analysis layer.

---

### Q9. What were the most difficult bugs you faced?

**Answer:**
Two stand out. First, a silent deduplication bug in the InterviewBit scraper: the URL discovery function was adding URLs to a `seen_urls` set, so when the extraction function later tried to fetch the same URLs, they were already marked as seen and returned `None`. The scraper appeared to work but silently collected zero experiences. This was only caught by checking scraper performance stats in the pipeline output.

Second, the scoring design problem — I initially used IDF re-ranking (log N/df) and it pushed Dynamic Programming and Arrays to the bottom because they appear in all experiences. Within a single company's corpus, high document frequency is a positive signal, not a sign of genericness. I replaced IDF with a consistency score (df/N) that boosts rather than penalises universally present topics.

---

### Q10. How would you improve this system if you had more time?

**Answer:**
Three directions. First, **cross-company IDF**: right now scoring is per-company only. A truly discriminative score would compute IDF across all companies — log(total_companies / companies_where_topic_appears) — so you can say "DP appears at Amazon AND Google AND Meta, so it's industry-wide; Leadership Principles appear only at Amazon, so that's Amazon-specific". That is the correct place for IDF in this system. Second, **smarter NLP**: replace the handcrafted keyword dictionary with a fine-tuned NER model that can identify technical topics from text without needing explicit keyword lists. This would catch niche topics the dictionary misses. Third, **user personalisation**: let users mark topics as known or studied, and have the system adjust recommendations based on their current skill level, not just raw topic frequency from the corpus.
