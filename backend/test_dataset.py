from datasets import load_dataset

ds = load_dataset(
    "neuralchemy/Prompt-injection-dataset",
    "core"
)

print("Train:", len(ds["train"]))
print("Validation:", len(ds["validation"]))
print("Test:", len(ds["test"]))

labels = set(ds["train"]["label"])
print("Labels:", labels)