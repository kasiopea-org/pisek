#include <iostream>
#include <unistd.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    while (t--) {
        long long a, b;
        cin >> a >> b;
        if (a > (long long) 1e9) {
            // Simulate a slow algorithm
            sleep(1);
        }
        cout << (a + b) << endl;
    }
}
