#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    if (argc != 3) {
        return 1;
    }

    int diff = std::atoi(argv[1]);

    // print out the difficulty
    std::cout << diff << std::endl;

    return 0;
}
