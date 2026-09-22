"""AI-assisted log anomaly detector - unsupervised ML on SIEM data.

Package layout:
    ingestion  -- SIEM log parsers (CSV, JSON, JSONL, Syslog, CEF, raw text)
    features   -- behavioral + text feature engineering
    models     -- unsupervised detectors (Isolation Forest, LOF, One-Class SVM,
                  nano autoencoder written in pure numpy)
    scoring    -- ensemble scoring, anomaly flagging and local explanations
    report     -- standalone HTML report generation
    sample_data -- synthetic SIEM event generator
"""

__version__ = "1.0.0"