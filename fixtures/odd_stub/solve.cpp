#include "odd.h"

void find_odd(std::vector<int> nums) {
    for (int num : nums)
        if (num % 2 == 1)
            report_odd(num);
}
