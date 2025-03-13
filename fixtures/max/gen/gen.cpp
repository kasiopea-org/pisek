#include <iostream>
#include <vector>

using std::cout;
using std::endl;
using std::vector;

#include "random.hpp"

vector<int> gen(std::string type) {
    int n;
    if (type == "small") {
        n = 10;
    } else if (type == "medium") {
        n = 100;
    } else if (type == "big") {
        n = 1000;
    } else {
        throw std::invalid_argument("Unknown type: " + type);
    }

    vector<int> input(n);
    for (size_t i=0; i<input.size(); i++) {
        input[i] = rand_range(1, n);
    }
    return input;
}  

int main(int argc, char *argv[]) {
    if (argc == 1) {
        cout <<  "small" << endl;
        cout <<  "medium" << endl;
        cout <<  "big" << endl;
    } else {
        int seed = strtoull(argv[2], NULL, 16) & 0x7fffffff;
        seed_rng(seed);
        vector<int> input = gen(argv[1]);
        cout << input.size() << endl;
        for (size_t i=0; i<input.size(); i++)
            cout << input[i] << " \n"[(i == input.size()-1)];
    }
}
