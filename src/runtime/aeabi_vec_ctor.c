#include <stddef.h>

/* Arm C++ ABI array-construction helper. The callback's result is ignored. */
/* Keep the original pointer in memory across callbacks, as observed in retail.
 * This GCC reconstruction is behavior-tested but does not match retail bytes.
 */
void *__aeabi_vec_ctor_nocookie_nodtor(void *volatile array,
                                    void *(*constructor)(void *),
                                    size_t element_size,
                                    size_t element_count)
{
    if (constructor != NULL) {
        unsigned char *element = array;
        while (element_count-- != 0) {
            constructor(element);
            element += element_size;
        }
    }
    return array;
}
