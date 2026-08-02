import viralai.api.schemas as s

print('fields', list(s.TrainModelFromDatasetResponse.model_fields.keys()))
print('schema', s.TrainModelFromDatasetResponse.model_json_schema())
