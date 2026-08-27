import re

with open("website/src/styles.css", "r") as f:
    css = f.read()

# Replace the tech-marquee-track with GPU-accelerated version
old = """.tech-marquee-track {
  display: flex;
  width: max-content;
  animation: marqueeScroll 30s linear infinite;
}
.tech-marquee-track:hover { animation-play-state: paused; }"""

new = """.tech-marquee-track {
  display: flex;
  width: max-content;
  will-change: transform;
  transform: translate3d(0, 0, 0);
  animation: marqueeScroll 40s linear infinite;
  -webkit-backface-visibility: hidden;
  backface-visibility: hidden;
}
.tech-marquee-track:hover { animation-play-state: paused; }"""

css = css.replace(old, new)

# Also fix the marquee section overflow
old2 = """.tech-marquee-section {
  padding: 48px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  overflow: hidden;
  background: var(--surface);
}"""

new2 = """.tech-marquee-section {
  padding: 48px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  overflow: hidden;
  background: var(--surface);
  contain: layout style;
}"""

css = css.replace(old2, new2)

with open("website/src/styles.css", "w") as f:
    f.write(css)

print("done")
