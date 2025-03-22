#include <vector>

template<typename T>
T max(std::vector<T> vec) {
    T res = 0;
    for (T element: vec) {
        res = std::max(res, element);
    }
    return res;
}
