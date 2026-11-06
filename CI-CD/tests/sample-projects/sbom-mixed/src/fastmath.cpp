// Sample project: small C++ extension module called from Python.
#include <pybind11/pybind11.h>

int add(int a, int b) { return a + b; }

PYBIND11_MODULE(fastmath, m) {
    m.def("add", &add, "Add two integers");
}
