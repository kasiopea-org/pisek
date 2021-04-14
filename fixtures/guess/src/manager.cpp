#include <iostream>

int think;
int queries = 0;

int ask(int x) {
    // std::cout << x << std::endl;
    queries++;
    if (queries > 20) {
        std::cout << "too many queries" << std::endl;
        exit(0);
    }
    return x - think;
}

int guessNumber();

int main() {
    std::cin >> think;
    int ans = guessNumber();

    if (ans == think) {
        std::cout << "ok" << std::endl;
    } else {
        std::cout << "wrong answer" << std::endl;
    }
}