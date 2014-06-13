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

def inol(intensity, reps):
    return reps/float(100-intensity)

def repopt_to_intensity(repopt):
    if repopt == 24: return "<70%"
    elif repopt == 18: return "70-79%"
    elif repopt == 15: return "80-89%"
    elif repopt == 7: return ">89%"

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

class SetsGenerator(object):
    def __init__(self, intensity_reps_map, set_limit_per_weight=0):
        self.reset()
        self.set_limit_per_weight = set_limit_per_weight
        self.intensity_reps_map = intensity_reps_map

    def reset(self):
        self.start = 0
        self.end = 0
        self.sets = []
        self.total_inol = 0
        self.total_reps = 0
        self.numsets = 0

    def generate(self, start, end):
        self.reset()
        self.start = start
        self.end = end

        repless = 0
        intensity = start
        while intensity < end:
            #reps = random.randint(replo, rephi)
            replo, rephi, repopt, repmax = reprange_for_intensity(intensity)
            key = (replo, rephi, repopt, repmax)
            reps_within = self.intensity_reps_map[key]
            #reps = rephi - repless
            reps = replo
            if reps < 1:
                reps = 1
            self.intensity_reps_map[key] += reps
            self.total_reps += reps
            set_inol = inol(intensity, reps)
            if intensity >= MINIMUM_INTENSITY_FOR_INOL:
                self.total_inol += set_inol
            theset = (intensity, reps, set_inol)
            self.sets.append(theset)
            repless += 1
            self.numsets += 1
            if self.set_limit_per_weight > 0 and self.numsets == self.set_limit_per_weight:
                intensity += WARMUP_INCREMENT
                self.numsets = 0

def generate_all_sets(max_intensity, target_inol, intensity_reps_map):
    """
    Return a list of (percent, rep, inol) pairs based on target (highest) intensity and inol
    percent is 0-100, rep is within the rep range, inol is calculated inol for that set.

    Calulation starts from 50% intensity.

    The sum of inols will be approximately target_inol.
    """

    setsgen = SetsGenerator(intensity_reps_map, WARMUP_SETS_PER_WEIGHT)
    setsgen.generate(50, max_intensity)

    sets = setsgen.sets[:]
    total_inol = setsgen.total_inol
    total_reps = setsgen.total_reps

    # generate target sets
    intensity = max_intensity

    total_reps = 0
    repopt = 1000
    replo, rephi, repopt, repmax = reprange_for_intensity(intensity)

    repdiff = (rephi - replo)/2
    set_reps = replo + (repdiff * target_inol)
    #set_reps = replo
    #target_reps = maxrep - set_reps
    #target_reps = (repopt + repmax)/2
    target_reps = repopt
    while total_inol < target_inol and total_reps < target_reps:
        replo, rephi, repopt, repmax = reprange_for_intensity(intensity)
        key = (replo, rephi, repopt, repmax)
        reps_within = intensity_reps_map[key]
        reps = set_reps

        intensity_reps_map[key] += reps
        total_reps += reps
        set_inol = inol(intensity, reps)
        if intensity >= MINIMUM_INTENSITY_FOR_INOL:
            total_inol += set_inol
        theset = (intensity, reps, set_inol)
        sets.append(theset)

    while total_inol < target_inol:
        #print "Missing inol, diff %.2f" % (target_inol - total_inol)

        intensity -= 5

        total_reps = 0
        repopt = 1000
        replo, rephi, repopt, repmax = reprange_for_intensity(intensity)
        set_reps = rephi
        numsets = 0
        while total_inol < target_inol and total_reps < repmax-set_reps and numsets < BACKOFF_SETS_PER_INTENSITY:
            #print "total_inol", total_inol
            #print "total_reps", total_reps
            #print "numsets", numsets
            replo, rephi, repopt, repmax = reprange_for_intensity(intensity)
            key = (replo, rephi, repopt, repmax)
            reps_within = intensity_reps_map[key]
            reps = set_reps

            intensity_reps_map[key] += reps
            total_reps += reps
            set_inol = inol(intensity, reps)
            total_inol += set_inol
            theset = (intensity, reps, set_inol)
            sets.append(theset)
            numsets += 1


    print "Total reps: %d, optimum reps: %d" % (total_reps, repopt)

    """
    totinol = 0
    for p, r, i in sets:
        w = barweight(p/100.0*maxweight)
        print "%3d%%: %5.1f x %d = INOL %.2f" % (p, w, r, i)
        totinol += i
    """

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

    sets = generate_all_sets(target_intensity, target_inol, intensity_reps_map)
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


