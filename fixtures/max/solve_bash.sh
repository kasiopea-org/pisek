#!/bin/bash

read N
read -a numbers

max=${numbers[0]}
for num in "${numbers[@]}"; do
    (( num > max )) && max=$num
done

echo $max
