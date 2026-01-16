import torch

DATASET_PATH = "./dataset_copydays"     # Local Data path 
MODEL_ID = "facebook/dinov2-base" #Change small to base for better accuracy
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 32 #change to 64 if better GPU is available
SIMILARITY_THRESHOLD = 0.92
HASH_SIZE = 8
HASH_THRESHOLD = 2
