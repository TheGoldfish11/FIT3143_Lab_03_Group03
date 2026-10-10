CC      = mpicc
CFLAGS  = -O2 -Wall -Wextra -fopenmp
LDFLAGS = -fopenmp

SRCS = main.c common.c node.c base.c
OBJS = $(SRCS:.c=.o)

wsn: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS)

%.o: %.c wsn.h
	$(CC) $(CFLAGS) -c $<

clean:
	rm -f wsn $(OBJS)

.PHONY: clean
