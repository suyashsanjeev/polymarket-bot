#!/bin/zsh
# runs continuous monitoring for bot script
source /Users/suyash/.venvs/pmarket/bin/activate
exec python /Users/suyash/Project_2/polymarket_bot/monitor.py \
        --monitor \
        --config /Users/suyash/Project_2/polymarket_bot/config.yaml

