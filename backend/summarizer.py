import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

class Summarizer:
    def __init__(self):
        # Using Falconsai/text_summarization (T5-based) for extreme speed and good quality
        self.model_name = "Falconsai/text_summarization"
        print(f"Loading model: {self.model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        
        # optimizing for CPU with dynamic quantization
        print("Quantizing model for CPU...")
        self.model = torch.quantization.quantize_dynamic(
            self.model, {torch.nn.Linear}, dtype=torch.qint8
        )
        print("Model loaded and quantized.")

    def chunk_text(self, text, max_tokens=500, overlap=50):
        """Splits text into chunks. T5 has a 512 token limit, so we use 500 safely."""
        inputs = self.tokenizer(text, return_tensors="pt", add_special_tokens=False)
        input_ids = inputs["input_ids"][0]
        
        chunks = []
        start = 0
        while start < len(input_ids):
            end = min(start + max_tokens, len(input_ids))
            chunk_ids = input_ids[start:end]
            chunks.append(self.tokenizer.decode(chunk_ids, skip_special_tokens=True))
            if end == len(input_ids):
                break
            start += max_tokens - overlap
        return chunks

    def fast_extractive_filter(self, text, compression_ratio=0.4):
        """
        Fast statistical filtering to remove less important sentences.
        """
        import re
        from collections import Counter

        # Simple sentence splitting
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
        if len(sentences) < 5: 
            return text

        # Word frequency
        words = re.findall(r'\w+', text.lower())
        stop_words = set(['the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'it', 'to', 'for', 'of', 'with', 'as', 'by'])
        words = [w for w in words if w not in stop_words]
        word_freq = Counter(words)
        
        # Score sentences
        sent_scores = []
        for i, sent in enumerate(sentences):
            score = 0
            sent_words = re.findall(r'\w+', sent.lower())
            if not sent_words: continue
            for w in sent_words:
                if w in word_freq:
                    score += word_freq[w]
            # Normalize by length
            sent_scores.append((i, score / len(sent_words)))
        
        # Keep top N
        num_keep = int(len(sentences) * compression_ratio)
        num_keep = max(num_keep, 5) 
        
        top_sentences = sorted(sent_scores, key=lambda x: x[1], reverse=True)[:num_keep]
        top_sentences.sort(key=lambda x: x[0]) 
        
        return " ".join([sentences[i] for i, _ in top_sentences])

    def summarize_stream(self, text: str, max_length=150, min_length=40):
        """Yields summary chunks."""
        print(f"DEBUG: summarize_stream called with text len {len(text)}")
        
        # 1. OPTIMIZATION: If text is huge (>20k chars), pre-filter it.
        if len(text) > 20000:
            print("DEBUG: Text > 20k, applying pre-filter...")
            yield "Processing large document (running fast filter)... "
            text = self.fast_extractive_filter(text, compression_ratio=0.5)
            print(f"DEBUG: Text reduced to len {len(text)}")
        
        tokens = self.tokenizer(text, return_tensors="pt", truncation=False)["input_ids"]
        print(f"DEBUG: Token count: {tokens.shape[1]}")
        
        # Chunking (T5 limit is 512, strict)
        if tokens.shape[1] > 500:
            chunks = self.chunk_text(text, max_tokens=500)
            yield f"Reading long document ({len(chunks)} sections)...\n\n"
            
            for i, chunk in enumerate(chunks):
                print(f"DEBUG: Processing chunk {i+1}/{len(chunks)}")
                summary_chunk = self._summarize_chunk(chunk, max_length=max_length, min_length=min_length)
                yield summary_chunk + " "
        else:
            print("DEBUG: Processing single chunk...")
            summary = self._summarize_chunk(text, max_length=max_length, min_length=min_length)
            yield summary

    def _summarize_chunk(self, text, max_length=150, min_length=40):
        # T5 requires strict prefix
        input_text = "summarize: " + text
        
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True)
        try:
            with torch.no_grad():
                summary_ids = self.model.generate(
                    inputs["input_ids"],
                    num_beams=4, # Higher beams for better quality (T5 is fast enough)
                    max_length=max_length,
                    min_length=min_length,
                    length_penalty=2.0,
                    early_stopping=True
                )
            decoded = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            return decoded
        except Exception as e:
            print(f"ERROR: {e}")
            return ""

summarizer_instance = Summarizer()
