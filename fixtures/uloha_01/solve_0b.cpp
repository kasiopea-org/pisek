#include <iostream>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int i = 0; i < t; i++) {
        long long a, b, c;
        cin >> a >> b;
        c = a + b;
        if (i == 9) {
            c++;
        }
        cout << c << endl;
    }
}
