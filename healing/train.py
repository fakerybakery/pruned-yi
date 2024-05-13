from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
import torch
max_seq_length = 8192
dtype = None
load_in_4bit = False

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "pruned-yi/pruned-yi-3b-untrained",
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj","gate_proj", "up_proj", "down_proj",],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
    use_rslora = False,
    loftq_config = None,
)

from datasets import load_dataset
dataset = load_dataset("pruned-yi/healing-data", split="train")
EOS_TOKEN = tokenizer.eos_token
def formatting_func(example):
    return example["text"] + EOS_TOKEN
print(dataset[0]['text'])
trainer = SFTTrainer(
    model = model,
    train_dataset = dataset,
    dataset_text_field = "text",
    tokenizer = tokenizer,
    max_seq_length = max_seq_length,
    packing = True, # Packs short sequences together to save time!
    formatting_func = formatting_func,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_ratio = 0.05,
        max_grad_norm = 1.0,
        num_train_epochs = 1,
        learning_rate = 2e-5,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.1,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)
trainer_stats = trainer.train()
model.save_pretrained_merged("adapter", tokenizer, save_method = "lora",)
model.save_pretrained_merged("merged_model", tokenizer, save_method = "merged_16bit",)