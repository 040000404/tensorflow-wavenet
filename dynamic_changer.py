
import numpy as np
import matplotlib.pyplot as plt
import terminalplot as tplt
import argparse

FORM = None

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--form', type=str, default=FORM)
    parser.add_argument('--min', type=float, default=0)
    parser.add_argument('--max', type=float, default=1)
    parser.add_argument('--period', type=float, default=1)
    parser.add_argument('--graph', type=str, default=None)
    return parser.parse_args()

def sine(min, max, period, step, samplesize):
    input = (np.pi*2/period)/samplesize*step
    range = max-min
    if range <= 0:
        raise Exception("wrong range of min-max")
    return (np.sin(input)*range*0.5+range*0.5+min)

def square(min, max, period, step, samplesize):
    input = (np.pi*2*period)/samplesize*step
    if max-min <= 0:
        raise Exception("wrong range of min-max")
    if sine(min, max, period, step,samplesize) > 0:
        return max
    elif sine(min, max, period, step, samplesize) <= 0:
        return min

def generate_value(step, samplesize, form, _min, _max, period):
    #array for graph plot
    x_array = []
    y_array = []
    arrays = [x_array, y_array]

    # outputs y_value as each x_value (step)
    for x in range(samplesize):
        x_array.append(step)
        if form == "sine":
            y_array.append(sine(_min, _max, period, step, samplesize))         
        elif form == "square":
            y_array.append(square(_min, _max, period, step, samplesize))
        else: raise Exception("wrong value on --form")
        step += 1
    return arrays

def generate_graph(arrays, graph):   
    #get x, y values to draw a graph
    x_array = arrays[0]
    y_array = arrays[1]

    #determine if show graph or not
    tplt.plot(x_array, y_array)
    if graph == 'terminal': #draw graph in terminal
        tplt.plot(x_array, y_array)
    elif graph == 'graphic': #generates new graphic window with matplotlib
        plt.scatter(x_array, y_array, color="green", marker="1", s=30)
        plt.xlabel('x_axis')
        plt.ylabel('y_axis')
        plt.title('plot')
        plt.show()
    elif graph == None:
        pass

def main():
    args = get_arguments()

    #set some arbitary values for step and samplesize
    # these values will be replaced with real values in generate.py
    step = 0
    samplesize = 16000

    generate_graph(generate_value(step, samplesize, args.form, args.min, args.max, args.period), args.graph)

if __name__ == '__main__':
    main()