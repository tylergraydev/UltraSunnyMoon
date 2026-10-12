/* Source-owned fixture for validating the REA/Ghidra connection. */
unsigned int rotate_mix(unsigned int x) {
    return ((x << 5) | (x >> 27)) ^ 0x13579bdfu;
}
int main(void) { return (int)rotate_mix(7); }
