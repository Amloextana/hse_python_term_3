#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Ошибка: неверное количество аргументов."
    exit 1
fi

FILE="$1"

if [ ! -e "$FILE" ]; then
    echo "Ошибка: файл '$FILE' не найден."
    exit 1
fi


declare -A day_revenue
declare -A day_label
declare -A item_qty
declare -A item_revenue

total_sales=0

while read -r date weekday item price qty; do

    line_revenue=$(awk "BEGIN { printf \"%.2f\", $price * $qty }")
    total_sales=$(awk "BEGIN { printf \"%.2f\", $total_sales + $line_revenue }")

    if [ -z "${day_revenue[$date]}" ]; then
        day_revenue[$date]=0
        day_label[$date]="$date $weekday"
    fi
    day_revenue[$date]=$(awk "BEGIN { printf \"%.2f\", ${day_revenue[$date]} + $line_revenue }")

    if [ -z "${item_qty[$item]}" ]; then
        item_qty[$item]=0
        item_revenue[$item]=0
    fi
    item_qty[$item]=$(( item_qty[$item] + qty ))
    item_revenue[$item]=$(awk "BEGIN { printf \"%.2f\", ${item_revenue[$item]} + $line_revenue }")

done < "$FILE"


echo "Общая сумма продаж: $total_sales"


best_day=""
best_day_revenue=0

for date in "${!day_revenue[@]}"; do
    rev="${day_revenue[$date]}"
    is_better=$(awk "BEGIN { print ($rev > $best_day_revenue) ? 1 : 0 }")
    if [ "$is_better" -eq 1 ]; then
        best_day_revenue="$rev"
        best_day="$date"
    fi
done

echo "День с наибольшей выручкой: ${day_label[$best_day]} (сумма продаж: $best_day_revenue)"


best_item=""
best_item_qty=0

for item in "${!item_qty[@]}"; do
    qty="${item_qty[$item]}"
    if [ "$qty" -gt "$best_item_qty" ]; then
        best_item_qty="$qty"
        best_item="$item"
    fi
done

echo "Популярный товар: $best_item (количество проданных единиц: $best_item_qty, сумма продаж: ${item_revenue[$best_item]})"
