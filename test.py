from transformers import pipeline

text = """The man from the West stopped suddenly and pulled his arm away. "You're not Jimmy Wells," he said. "Twenty years is a long time, but not long enough to change the shape of a man's nose." "It sometimes changes a good man into a bad one," said the tall man. "You've been under arrest for ten minutes, Bob. Chicago cops thought you might be coming to New York. They told us to watch for you. Are you coming with me quietly? That's wise."""

prompt = f"Describe the style, mood, and main themes of this literary text in 2 sentences:\n\n{text}"

print("=== BART-CNN ===")
bart = pipeline("summarization", model="facebook/bart-large-cnn")
r = bart(prompt, max_length=60, min_length=20, no_repeat_ngram_size=3)
print(r[0]["summary_text"])

print("\n=== DistilBART ===")
distil = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
r = distil(prompt, max_length=60, min_length=20, no_repeat_ngram_size=3)
print(r[0]["summary_text"])

print("\n=== FLAN-T5 ===")
flan = pipeline("text2text-generation", model="google/flan-t5-base")
r = flan(prompt, max_new_tokens=80, no_repeat_ngram_size=3)
print(r[0]["generated_text"])