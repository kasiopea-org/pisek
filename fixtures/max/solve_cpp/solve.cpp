#include <iostream>
#include <vector>
#include "max.hpp"

using std::cin;
using std::cout;
using std::endl;
using std::vector;

int main() {
    int n;
    cin >> n;
    vector<int> inp(n);
    for (int i=0; i<n; i++) {
        cin >> inp[i];
    }
    cout << max(inp) << endl;
}
