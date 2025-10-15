#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/wait.h>

int main(int argc, char *argv[])
{
    printf("hello (pid:%d)\n", (int)getpid());

    int rc = fork();
    if (rc < 0)
    {
        fprintf(stderr, "fork failed\n");
        exit(1);
    }
    else if (rc == 0)
    {
        // 👶 child (new process)
        printf("child (pid:%d)\n", (int)getpid());

        // 🔄 Transform into 'wc' program
        char *myargs[3];
        myargs[0] = strdup("wc");   // program name
        myargs[1] = strdup("p3.c"); // argument: file to count
        myargs[2] = NULL;           // end-of-array marker

        execvp(myargs[0], myargs); // 🚀 TRANSFORM!

        printf("this shouldn't print out"); // Never reached!
    }
    else
    {
        // 👨 parent
        int rc_wait = wait(NULL);
        printf("parent of %d (rc_wait:%d) (pid:%d)\n",
               rc, rc_wait, (int)getpid());
    }

    return 0;
}