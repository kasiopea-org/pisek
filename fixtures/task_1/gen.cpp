#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    if (argc != 3) {
        return 1;
    }

    int diff = std::atoi(argv[1]);
    int seed = std::strtoull(argv[2], NULL, 16) & 0x7fffffff;

    // print out the difficulty
    std::cout << diff << std::endl;

    // print out the seed
    std::cout << seed << std::endl;

    return 0;
}
