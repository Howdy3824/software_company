export OUTPUT_DIR=bart_cnn_finetune

# Make output directory if it doesn't exist
mkdir -p $OUTPUT_DIR

# Add parent directory to python path to access lightning_base.py
export PYTHONPATH="../":"${PYTHONPATH}"


# --model_name_or_path=t5-base for t5

python finetune.py \
    --model_name_or_path=facebook/bart-large \
    --learning_rate=3e-5 \
    --fp16 \
    --gpus 1 \
    --do_train \
    --do_predict \
    --n_val 1000 \
    --val_check_interval 0.1 \
    --sortish_sampler \
    --max_target_length=56 \
    $@
