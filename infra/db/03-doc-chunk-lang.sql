-- Language of each document chunk ('el' or 'en'), so cross-language matches can use their own cutoff.
ALTER TABLE doc_chunks ADD COLUMN IF NOT EXISTS lang TEXT;
