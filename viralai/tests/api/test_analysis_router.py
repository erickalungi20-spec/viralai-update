# "ATGCAATAA": M-Q-stop, same fixture gene used across every prior phase's tests
REFERENCE_GENOME = "ATGCAATAA"
QUERY_GENOME = "ATGCTATAA"  # single missense substitution at position 4
GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]


def test_detect_mutations(client):
    response = client.post(
        "/analysis/mutations",
        json={"reference_genome": REFERENCE_GENOME, "query_genome": QUERY_GENOME},
    )

    assert response.status_code == 200
    mutations = response.json()["mutations"]
    assert len(mutations) == 1
    assert mutations[0]["position"] == 4


def test_analyze_proteins(client):
    mutation_response = client.post(
        "/analysis/mutations",
        json={"reference_genome": REFERENCE_GENOME, "query_genome": QUERY_GENOME},
    )
    mutations = mutation_response.json()["mutations"]

    protein_response = client.post(
        "/analysis/proteins",
        json={
            "reference_genome": REFERENCE_GENOME,
            "mutations": mutations,
            "gene_annotations": GENE_ANNOTATIONS,
        },
    )

    assert protein_response.status_code == 200
    protein_mutations = protein_response.json()["protein_mutations"]
    assert len(protein_mutations) == 1
    assert protein_mutations[0]["classification"] == "missense"


def test_evolution_summary(client):
    response = client.post(
        "/analysis/evolution",
        json={"aligned_population": [REFERENCE_GENOME, QUERY_GENOME, REFERENCE_GENOME]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["population_size"] == 3
    assert body["nucleotide_diversity"] >= 0.0


def test_detect_mutations_with_identical_genomes_returns_empty(client):
    response = client.post(
        "/analysis/mutations",
        json={"reference_genome": REFERENCE_GENOME, "query_genome": REFERENCE_GENOME},
    )
    assert response.json()["mutations"] == []


def test_detect_mutations_missing_field_returns_422(client):
    response = client.post("/analysis/mutations", json={"reference_genome": REFERENCE_GENOME})
    assert response.status_code == 422
