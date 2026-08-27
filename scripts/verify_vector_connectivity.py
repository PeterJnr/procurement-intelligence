import os
import time
import uuid

from dotenv import load_dotenv
from pinecone import Pinecone

from app.services.huggingface_embeddings import create_embedding


def main() -> None:
    load_dotenv()
    test_id = f"connectivity-test-{uuid.uuid4()}"
    client = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    description = client.describe_index(os.environ["PINECONE_INDEX_NAME"])
    index = client.Index(host=description.host)
    namespace = os.environ["PINECONE_NAMESPACE"]
    embedding = create_embedding(
        "Dell Latitude 5440 business laptop Intel Core i5 "
        "16GB RAM 512GB SSD new"
    )

    try:
        index.upsert(
            vectors=[
                {
                    "id": test_id,
                    "values": embedding,
                    "metadata": {"record_type": "connectivity_test"},
                }
            ],
            namespace=namespace,
        )
        for _ in range(5):
            response = index.fetch(ids=[test_id], namespace=namespace)
            if test_id in response.vectors:
                break
            time.sleep(2)
        else:
            raise RuntimeError("Temporary vector was not fetchable")

        response = index.query(
            vector=embedding,
            top_k=10,
            namespace=namespace,
            include_metadata=True,
        )
        if not any(match.id == test_id for match in response.matches):
            raise RuntimeError(
                "Temporary vector was not returned by similarity query"
            )

        print("embedding=created")
        print("upsert=verified")
        print("fetch=verified")
        print("similarity_query=verified")
    finally:
        index.delete(ids=[test_id], namespace=namespace)
        for _ in range(5):
            response = index.fetch(ids=[test_id], namespace=namespace)
            if test_id not in response.vectors:
                print("temporary_vector_deletion=verified")
                break
            time.sleep(2)
        else:
            raise RuntimeError("Temporary vector deletion could not be verified")


if __name__ == "__main__":
    main()
