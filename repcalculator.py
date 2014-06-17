#!/usr/bin/env python

import sys
import random

MINIMUM_INTENSITY_FOR_INOL = 50
BACKOFF_SETS_PER_INTENSITY = 1
MAX_SETS = 19
WARMUP_SETS_PER_WEIGHT = 2
WARMUP_INCREMENT = 10

#
# Calculate reps according to Prilepin's table.
#
# Intensity     Rep range   Reps total      Optimal reps
# <70%          3-6         18-30           24
# 70-79%        3-6         12-24           18
# 80-89%        2-4         10-20           15
# >89%          1-2         4-10            7
#

def calc_inol(intensity, reps):
    return reps/float(100-intensity)

def repopt_to_intensity(repopt):
    if repopt == 24: return "<70%"
    elif repopt == 18: return "70-79%"
    elif repopt == 15: return "80-89%"
    elif repopt == 7: return ">89%"

class RepRange(object):
    reps = {}
    def __init__(self, intensity):
        if intensity < 70:
            replo, rephi, repopt, repmax = 3, 6, 24, 30
        elif intensity < 80:
            replo, rephi, repopt, repmax = 3, 6, 18, 24
        elif intensity < 90:
            replo, rephi, repopt, repmax = 2, 4, 15, 20
        else:
            replo, rephi, repopt, repmax = 1, 2, 7, 10

        self.intensity = intensity
        self.low = replo
        self.high = rephi
        self.optimal = repopt
        self.repmax = repmax

    def __hash__(self):
        t = (self.low, self.high, self.optimal, self.repmax)
        #print "hash(",t,") to", hash(t)
        return hash(t)

    def __eq__(self, another):
        """for hashing to work properly"""
        return hasattr(another, 'low') and \
               hasattr(another, 'high') and \
               hasattr(another, 'optimal') and \
               hasattr(another, 'repmax') and \
               another.low == self.low and \
               another.high == self.high and \
               another.optimal == self.optimal and \
               another.repmax == self.repmax

    def __str__(self):
        t = (self.low, self.high, self.optimal, self.repmax)
        return str(t)

    @classmethod
    def __assert_reps(klass):
        if len(klass.reps.keys()) == 0:
            for i in range(0, 101):
                rr = RepRange(i)
                klass.reps[rr] = 0

    @classmethod
    def add(klass, repsrange, repcount):
        klass.__assert_reps()
        #print "Add", repcount, "reps to", repsrange
        klass.reps[repsrange] += repcount

    @classmethod
    def count(klass, intensity):
        klass.__assert_reps()
        rr = RepRange(intensity)
        return klass.reps[rr]

def reprange_for_intensity(intensity):
    if intensity < 70:
        replo, rephi, repopt, repmax = 3, 6, 24, 30
    elif intensity < 80:
        replo, rephi, repopt, repmax = 3, 6, 18, 24
    elif intensity < 90:
        replo, rephi, repopt, repmax = 2, 4, 15, 20
    else:
        replo, rephi, repopt, repmax = 1, 2, 7, 10

    return replo, rephi, repopt, repmax

def barweight(w):
    return round(w/2.5)*2.5

class Set(object):
    def __init__(self, intensity, reps, weight1rm):
        self.intensity = intensity
        self.weight1rm = weight1rm
        self.reps = reps
        self.inol = reps / float(100-intensity)
        self.weight = intensity/100.0 * weight1rm
        self.weight = float(int(self.weight/2.5) * 2.5)

    def __str__(self):
        return "%d reps at %d%% / %.2f => %3.2f kg" % (self.reps,
                                                       self.intensity,
                                                       self.inol, self.weight)

class Sets(object):
    def __init__(self):
        self.sets = []

    def append(self, s):
        self.sets.append(s)

    def count(self):
        return len(self.sets)

    def inol(self):
        return sum(map(lambda x: x.inol if x.intensity >= MINIMUM_INTENSITY_FOR_INOL else 0, self.sets))

    def reps(self):
        return sum(map(lambda x: x.reps, self.sets))

class SetsGenerator(object):
    def __init__(self, intensity_reps_map, maxweight, set_limit_per_weight=0):
        self.reset()
        self.set_limit_per_weight = set_limit_per_weight
        self.intensity_reps_map = intensity_reps_map
        self.maxweight = maxweight

    def reset(self):
        self.start = 0
        self.end = 0

    def generate(self, start, end):
        sets = []
        self.reset()
        self.start = start
        self.end = end

        total_inol = 0
        total_reps = 0
        ss = Sets()

        numsets = 0
        intensity = start
        while intensity < end:

            #rr = RepRange(intensity)

            replo, rephi, repopt, repmax = reprange_for_intensity(intensity)
            key = (replo, rephi, repopt, repmax)
            reps_within = self.intensity_reps_map[key]
            reps = replo

            #rr.add(reps)

            self.intensity_reps_map[key] += reps

            s = Set(intensity, reps, self.maxweight)
            ss.append(s)

            numsets += 1
            if self.set_limit_per_weight > 0 and numsets == self.set_limit_per_weight:
                intensity += WARMUP_INCREMENT
                numsets = 0

        #print "Total inol", total_inol, "vs Sets.inol():", ss.inol()
        #return (sets[:], total_inol, total_reps)
        return ss

class Generator(object):
    MINIMAL_LOAD = 0
    LOW_LOAD = 1
    NORMAL_LOAD = 2
    HIGH_LOAD = 3
    def __init__(self, weight1rm, start, end, increment, num_sets_per_intensity, load, initial_inol, target_inol):
        """Generate sets based on input parameters.
        start                       intensity
        end                         intensity, not including
        target_inol                 target inol
        num_sets_per_intensity      0=inf, else 1..N
        """
        self.start = start
        self.end = end
        self.increment = increment
        self.num_sets_per_intensity = num_sets_per_intensity
        self.load = load
        self.target_inol = target_inol
        self.initial_inol = initial_inol
        self.weight1rm = weight1rm
        self.inol = 0

    def _calculate_rep_count(self, intensity, rr):
        count = 0
        if self.load == Generator.MINIMAL_LOAD:
            count = 1
        elif self.load == Generator.LOW_LOAD:
            count = rr.low
        elif self.load == Generator.NORMAL_LOAD:
            count = int(rr.low + (rr.high - rr.low)/2.0)
        elif self.load == Generator.HIGH_LOAD:
            count = rr.high
        else:
            raise Exception("Invalid value %s for load" % str(self.load))
        return count

    def next(self):
        intensity = self.start
        inol = self.initial_inol
        numsets = 0

        optimal_rep_range = True
        intensity_goal_reached = False

        while not intensity_goal_reached and inol <= self.target_inol and optimal_rep_range:

            rr = RepRange(intensity)
            count = self._calculate_rep_count(intensity, rr)

            s = Set(intensity, count, self.weight1rm) # last param is weight1rm
            inol += s.inol

            RepRange.add(rr, count)

            # XXX: This is the optimal/maxrep value -- maxrep for high load?
            count = RepRange.count(intensity)
            if count >= rr.optimal:
                optimal_rep_range = False

            numsets += 1
            # if 0 sets per intensity, just continue until inol or rep target is reached
            if self.num_sets_per_intensity > 0 and numsets == self.num_sets_per_intensity:
                intensity += self.increment
                numsets = 0
                if self.start == self.end:
                    intensity_goal_reached = True

            if self.start < self.end and intensity > self.end:
                intensity_goal_reached = True
            elif self.start > self.end and intensity < self.end:
                intensity_goal_reached = True

            self.inol += s.inol
            yield s

class WarmupGenerator(Generator):
    START_INTENSITY = 50
    def __init__(self, weight1rm, end, load, tinol):
        start = WarmupGenerator.START_INTENSITY + (end % 10)
        super(WarmupGenerator, self).__init__(weight1rm, start, end, 10, 2, load, 0, tinol)

    def _calculate_rep_count(self, intensity, rr):
        count = super(WarmupGenerator, self)._calculate_rep_count(intensity, rr)

        # except...

        if intensity >= 75:
            count = 1

        return count

class BackoffGenerator(Generator):
    def __init__(self, weight1rm, start, inol, tinol):
        super(BackoffGenerator, self).__init__(weight1rm, start, 50, 10, 0, Generator.HIGH_LOAD, inol, tinol)

def generate_all_sets(max_intensity, target_inol, intensity_reps_map, maxweight):
    """
    Return a list of (percent, rep, inol) pairs based on target (highest) intensity and inol
    percent is 0-100, rep is within the rep range, inol is calculated inol for that set.

    Calulation starts from 50% intensity.

    The sum of inols will be approximately target_inol.
    """

    warmup_gen = SetsGenerator(intensity_reps_map, maxweight, WARMUP_SETS_PER_WEIGHT)
    #sets, total_inol, total_reps = warmup_gen.generate(50, max_intensity)
    ss = warmup_gen.generate(50, max_intensity)

    warmup_load = Generator.LOW_LOAD
    if target_inol >= 1.0 and max_intensity < 90:
        warmup_load = Generator.NORMAL_LOAD

    work_load = Generator.LOW_LOAD
    if target_inol >= 1.0 and max_intensity < 90:
        work_load = Generator.NORMAL_LOAD

    sets = []

    print "%d%% for INOL %.2f with max %d" % (max_intensity, target_inol, maxweight)

    increment = 10
    inol = 0
    print "\n---- Warmup"
    warmup = WarmupGenerator(maxweight, max_intensity-increment, warmup_load, target_inol)
    for s in warmup.next():
        print s
        sets.append(s)
        inol += s.inol

    print "\n---- Workout"
    workout = Generator(maxweight, max_intensity, max_intensity, increment, 0, work_load, warmup.inol, target_inol)
    for s in workout.next():
        print s
        sets.append(s)


    print "\n---- Backoff"
    backoff = BackoffGenerator(maxweight, max_intensity-increment, warmup.inol + workout.inol, target_inol)
    for s in backoff.next():
        print s
        inol += s.inol


    print "\nStatistics:"
    print "* Warmup: %.2f" % (warmup.inol)
    print "* Workout: %.2f" % (workout.inol)
    if backoff.inol:
        print "* Backoff: %.2f" % (backoff.inol)
    print "Total: %.2f" % (warmup.inol + workout.inol + backoff.inol)
    print
    print "Reps:"
    for key, value in RepRange.reps.items():
        print "*", key, "=", value
    print ""

    reps = [s.reps for s in sets]
    reps += [0] * (MAX_SETS - len(reps))
    percentages = [s.intensity for s in sets]
    percentages += [0] * (MAX_SETS - len(percentages))
    print
    for l in reps: print "%d;" % l,
    print
    for l in percentages: print "%d;" % l,
    print
    print


    sys.exit(1)
    sets = [(s.intensity, s.reps, s.inol) for s in ss.sets]

    # generate target sets
    intensity = max_intensity

    total_reps = 0
    total_inol = 0
    repopt = 1000
    replo, rephi, repopt, repmax = reprange_for_intensity(intensity)

    repdiff = (rephi - replo)/2
    set_reps = replo + (repdiff * target_inol)
    target_reps = repopt
    while total_inol < target_inol and total_reps < target_reps:
        replo, rephi, repopt, repmax = reprange_for_intensity(intensity)
        key = (replo, rephi, repopt, repmax)
        reps_within = intensity_reps_map[key]
        reps = set_reps

        intensity_reps_map[key] += reps
        total_reps += reps
        set_inol = calc_inol(intensity, reps)
        if intensity >= MINIMUM_INTENSITY_FOR_INOL:
            total_inol += set_inol
        theset = (intensity, reps, set_inol)
        sets.append(theset)

    while total_inol < target_inol:
        intensity -= 5

        total_reps = 0
        repopt = 1000
        replo, rephi, repopt, repmax = reprange_for_intensity(intensity)
        set_reps = rephi
        numsets = 0
        while total_inol < target_inol and total_reps < repmax-set_reps and numsets < BACKOFF_SETS_PER_INTENSITY:
            replo, rephi, repopt, repmax = reprange_for_intensity(intensity)
            key = (replo, rephi, repopt, repmax)
            reps_within = intensity_reps_map[key]
            reps = set_reps

            intensity_reps_map[key] += reps
            total_reps += reps
            set_inol = calc_inol(intensity, reps)
            total_inol += set_inol
            theset = (intensity, reps, set_inol)
            sets.append(theset)
            numsets += 1


    print "Total reps: %d, optimum reps: %d" % (total_reps, repopt)

    print
    for (replo, rephi, repopt, repmax), reps in intensity_reps_map.items():
        intensity = repopt_to_intensity(repopt)
        print "%d reps (opt %d, max %d) at %s (%d, %d)" % (reps, repopt, repmax, intensity, replo, rephi)

    print

    return sets

def init_intensity_map():
    m = {}
    for i in range(0, 100):
        key = reprange_for_intensity(i)
        m[key] = 0
    return m

def main():
    if len(sys.argv) < 3:
        print "usage: %s <inol> <intensity> <1rm>" % (sys.argv[0])
        print """
    <inol>          0..2: Float
    <intensity>     0..100: Integer (percent)
    <1rm>           0..: Integer (kg)
    """
        sys.exit(0)

    maxweight = 100
    if len(sys.argv) == 4:
        maxweight = int(sys.argv[3])

    target_inol = float(sys.argv[1])
    target_intensity = int(sys.argv[2])

    newsets = []
    intensity_reps_map = init_intensity_map()

    sets = generate_all_sets(target_intensity, target_inol, intensity_reps_map, maxweight)
    totinol = 0
    for p, r, i in sets:
        w = barweight(p/100.0*maxweight)
        newsets.append((p, w, r, i))
        print "%3d%%: %5.1f x %d = INOL %.2f" % (p, w, r, i)
        if p >= MINIMUM_INTENSITY_FOR_INOL:
            totinol += i

    print
    print "Total INOL %.2f at maximum intensity %d" % (totinol, target_intensity)

    newsets = map(list, zip(*newsets))
    newsets[0] += [0] * (MAX_SETS-len(newsets[0]))
    newsets[2] += [0] * (MAX_SETS-len(newsets[2]))
    print
    for l in newsets[2]: print "%d;" % l,
    print
    for l in newsets[0]: print "%d;" % l,
    print

    #print
    #for l in newsets[1]: print "%7.1f;" % l,
    #print
    #for l in newsets[3]: print "%7.2f;" % l,

    print

if __name__ == '__main__':
    main()


