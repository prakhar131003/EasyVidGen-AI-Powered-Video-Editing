# This module is no longer used for splitting; we split by duration.
class SemanticChunker:
    def chunk_text(self, text: str) -> list:
        # Return the text as a single chunk – actual splitting is done by time.
        return [text]