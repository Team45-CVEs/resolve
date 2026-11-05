/* Test fixture: links cJSON 1.7.17, which has CVE-2024-31755
 * (NULL pointer dereference in cJSON_SetValuestring).
 * The call below gives later stages (reach) a path from main to that function. */
#include <stdio.h>
#include "cJSON.h"

int main(void)
{
    cJSON *obj = cJSON_CreateObject();
    cJSON *name = cJSON_AddStringToObject(obj, "name", "resolve");

    cJSON_SetValuestring(name, "team45");

    char *text = cJSON_PrintUnformatted(obj);
    printf("%s\n", text);

    cJSON_free(text);
    cJSON_Delete(obj);
    return 0;
}
