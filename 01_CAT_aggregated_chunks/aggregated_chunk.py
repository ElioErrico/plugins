from cat.mad_hatter.decorators import hook
from langchain.docstore.document import Document

from cat.log import log


def _build_aggregated_metadata(chunk_group):
    """Mantiene i metadata condivisi dal gruppo e marca il chunk aggregato."""
    if not chunk_group:
        return {}

    shared_metadata = dict(getattr(chunk_group[0], "metadata", {}) or {})
    for chunk in chunk_group[1:]:
        current_metadata = dict(getattr(chunk, "metadata", {}) or {})
        for key in list(shared_metadata.keys()):
            if current_metadata.get(key) != shared_metadata[key]:
                shared_metadata.pop(key)

    shared_metadata["aggregated_chunk"] = True
    shared_metadata["aggregated_chunk_size"] = len(chunk_group)
    return shared_metadata


@hook
def after_rabbithole_splitted_text(chunks, cat):
    settings = cat.mad_hatter.get_plugin().load_settings()
    
    if settings.get("enable_classification", True):  # Default to True if not set
        # Define classification labels
        classification_labels = {
            "useful": ["relevant", "important", "useful", "meaningful"],
            "no sense": ["nonsense", "gibberish", "random", "unclear"],
            "header or footer": ["copyright", "footer", "header", "page number", "confidential"]
        }
        filtered_chunks = []
        for chunk in chunks:
            classification = cat.classify(chunk.page_content, labels=classification_labels)
            cat.send_ws_message(classification)
            if classification in ["useful"]:
                filtered_chunks.append(chunk)
    else:
        filtered_chunks = chunks  # Skip classification if disabled

    # Original aggregation logic on filtered chunks
    n_of_chunks = max(1, int(settings.get("n_of_chunks", 5)))
    aggregated_chunks = []

    for i in range(0, len(filtered_chunks), n_of_chunks):
        chunk_group = filtered_chunks[i:i + n_of_chunks]
        concatenated_content = ''.join(chunk.page_content for chunk in chunk_group)
        if not concatenated_content.strip():
            continue

        concatenated_new_document = Document(
            page_content=concatenated_content,
            metadata=_build_aggregated_metadata(chunk_group),
        )
        aggregated_chunks.append(concatenated_new_document)

    log.info(
        f"[Aggregated Chunks] Filtered chunks: {len(filtered_chunks)}, aggregated chunks: {len(aggregated_chunks)}"
    )
    
    return filtered_chunks + aggregated_chunks
