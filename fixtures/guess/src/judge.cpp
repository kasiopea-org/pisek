#include <fstream>
#include <iostream>

const int OPT_QUERIES = 10;
const int MAX_QUERIES = 20;

void verdict(double points, std::string msg) {
    std::cerr << msg << std::endl;
    std::cout << points << std::endl;

    std::exit(0);
}

int main(int argc, char **argv) {
    if (argc < 3)
        return 1;

    std::ofstream send(argv[2], std::ios::out);
    std::ifstream recv(argv[1], std::ios::in);

    int target;
    std::cin >> target;

    int queries = 0;

    while (true) {
        char type;
        int query;

        if (!(recv >> type >> query))
            verdict(0, "Protocol violation");

        if (type == '?') {
            if (queries == MAX_QUERIES) {
                send << -1 << std::endl;
                verdict(0, "Query limit exceeded");
            }

            send << (query == target) << std::endl;
        } else if (type == '!') {
            if (query == target) {
                double score = double(OPT_QUERIES) / double(queries);

                if (score >= 1.0)
                    verdict(1.0, "translate:success");
                else
                    verdict(score, "translate:partial");
            } else {
                verdict(0, "translate:wrong");
            }
        } else {
            verdict(0, "Protocol violation");
        }

        queries++;
    }
}
