# Architecture

## Request flow

1. Frontend uploads or replays one Fitbit segment at a time.
2. Backend stores the raw segment.
3. Backend extracts tabular features.
4. Predictor returns class probabilities.
5. Backend loads user profile and rolling memory.
6. Backend sends the assembled payload to Dify.
7. Frontend displays probabilities and Dify-generated explanation.

## State split

- Long-term memory: `user_profiles`
- Short-term rolling memory: `memory_snapshots`
- Raw segment storage: `raw_segments`
- Feature storage: `feature_vectors`
- Prediction storage: `model_predictions`
- Dify request/response audit: `dify_runs`

## Why Dify is behind the model

- Structured storage and feature extraction are easier to version in your own backend.
- XGBoost model loading is more stable in your own Python service than in Dify workflow code sandboxes.
- Personalized prompt prefixes should come from your own user profile store, not only from session variables.
