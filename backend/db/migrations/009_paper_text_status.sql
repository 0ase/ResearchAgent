ALTER TABLE research_papers
    ADD COLUMN full_text_status TEXT NOT NULL DEFAULT 'unavailable';
