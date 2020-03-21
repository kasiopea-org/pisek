#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    // oops!
    a = abs(a);
    b = abs(b);
    cout << (a + b) << endl;
}
