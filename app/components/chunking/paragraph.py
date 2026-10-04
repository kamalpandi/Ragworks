from .base import BaseChunkingStrategy


class ParagraphChunkingStrategy(BaseChunkingStrategy):
    def __init__(self, chunk_size: int = 1000, overlap_size: int = 200):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size

    def chunk(self, text: str) -> list[str]:
        # 1. Split text into atomic units (paragraphs)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk_paragraphs = []
        current_len = 0

        for paragraph in paragraphs:
            para_len = len(paragraph)

            # 2. Check if adding this paragraph exceeds limit
            # (We add 2 chars for the "\n\n" joiner)
            if current_chunk_paragraphs and (
                current_len + para_len + 2 > self.chunk_size
            ):
                # A. Finalize the current chunk
                chunks.append("\n\n".join(current_chunk_paragraphs))

                # B. Create Overlap for the next chunk
                # We work backwards from the current chunk to find text that fits in overlap_size
                overlap_buffer = []
                overlap_len = 0

                for p in reversed(current_chunk_paragraphs):
                    if overlap_len + len(p) <= self.overlap_size:
                        overlap_buffer.insert(0, p)
                        overlap_len += len(p)
                    else:
                        break

                # C. Start new chunk with overlap
                current_chunk_paragraphs = overlap_buffer
                current_len = overlap_len

            # 3. Add the current paragraph
            current_chunk_paragraphs.append(paragraph)
            current_len += para_len

        # 4. Add the final remaining chunk
        if current_chunk_paragraphs:
            chunks.append("\n\n".join(current_chunk_paragraphs))

        return chunks
