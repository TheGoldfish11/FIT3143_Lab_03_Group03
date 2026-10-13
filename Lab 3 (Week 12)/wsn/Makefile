CC      = mpicc

# Apple clang has no -fopenmp of its own; it needs libomp (brew install libomp open-mpi)
ifeq ($(shell uname -s),Darwin)
  LIBOMP   := $(shell brew --prefix libomp 2>/dev/null)
  OMPFLAGS  = -Xpreprocessor -fopenmp -I$(LIBOMP)/include
  OMPLIBS   = -L$(LIBOMP)/lib -lomp
else
  OMPFLAGS  = -fopenmp
  OMPLIBS   = -fopenmp
endif

CFLAGS  = -O2 -Wall -Wextra $(OMPFLAGS)
LDFLAGS = $(OMPLIBS)

SRCS = main.c common.c node.c base.c
OBJS = $(SRCS:.c=.o)

wsn: $(OBJS)
	$(CC) -o $@ $(OBJS) $(LDFLAGS)

%.o: %.c wsn.h
	$(CC) $(CFLAGS) -c $<

clean:
	rm -f wsn $(OBJS)

.PHONY: clean
