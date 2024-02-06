#include "odd.h"

#include <algorithm>
#include <iostream>

namespace {
std::vector<int> reported;
}

void report_odd(int number) {
    reported.push_back(number);
}

int main() {
    std::vector<int> numbers;

    {
        int num;
        while (std::cin >> num)
            numbers.push_back(num);
    }

    find_odd(numbers);

    std::sort(reported.begin(), reported.end());

    for (int num : reported)
        std::cout << num << "\n";
}
