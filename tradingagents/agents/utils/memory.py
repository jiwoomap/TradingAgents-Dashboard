import os
import chromadb
from chromadb.config import Settings
from openai import OpenAI


class FinancialSituationMemory:
    def __init__(self, name, config):
        if config["backend_url"] == "http://localhost:11434/v1":
            self.embedding = "nomic-embed-text"
        else:
            self.embedding = "text-embedding-3-small"
        self.client = OpenAI(base_url=config["backend_url"])
        # Use PersistentClient to save data to disk
        db_path = os.path.join(config.get("project_dir", "."), "chroma_db")
        self.chroma_client = chromadb.PersistentClient(path=db_path, settings=Settings(allow_reset=True))
        self.situation_collection = self.chroma_client.get_or_create_collection(name=name)

    def get_embedding(self, text):
        """Get OpenAI embedding for a text"""
        
        response = self.client.embeddings.create(
            model=self.embedding, input=text
        )
        return response.data[0].embedding

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using OpenAI embeddings"""
        query_embedding = self.get_embedding(current_situation)

        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matched_results = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                matched_results.append(
                    {
                        "matched_situation": results["documents"][0][i],
                        "recommendation": results["metadatas"][0][i]["recommendation"],
                        "similarity_score": 1 - results["distances"][0][i],
                    }
                )

        return matched_results

    def load_from_obsidian(self, vault_path):
        """Load markdown files from an Obsidian vault into memory"""
        import os
        import glob
        
        if not os.path.exists(vault_path):
            return f"Error: Obsidian path not found: {vault_path}"

        md_files = glob.glob(os.path.join(vault_path, "**/*.md"), recursive=True)
        new_data = []
        count = 0
        
        for file_path in md_files:
            try:
                # Skip system files or hidden files
                if "/." in file_path or "\\." in file_path:
                    continue
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        continue
                        
                    filename = os.path.basename(file_path)
                    
                    # Strategy: Use Filename + Start of content as 'Situation' context
                    # Use full content as 'Recommendation/Knowledge'
                    # This allows retrieving the note when context matches the title/intro
                    situation_context = f"Note Title: {filename}\nContext: {content[:300]}"
                    
                    new_data.append((situation_context, content))
                    count += 1
            except Exception as e:
                print(f"Failed to read {file_path}: {e}")
        
        if new_data:
            self.add_situations(new_data)
            return f"Successfully loaded {count} notes from Obsidian vault."
        else:
            return "No markdown files found in the specified path."

    def save_to_obsidian(self, content, filename, vault_path, folder="TradingAgents/Reports"):
        """Save a report to the Obsidian vault"""
        import os
        
        if not os.path.exists(vault_path):
            return False, f"Vault path not found: {vault_path}"
            
        full_dir = os.path.join(vault_path, folder)
        os.makedirs(full_dir, exist_ok=True)
        
        file_path = os.path.join(full_dir, filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"Saved to {file_path}"
        except Exception as e:
            return False, f"Failed to save: {str(e)}"


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
