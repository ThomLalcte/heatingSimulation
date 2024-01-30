from matplotlib import pyplot as plt
import numpy as np, random, matplotlib.animation as animation, json


class cell:

    class cellType:
        heatSink = 1
        conductor = 2

    def __init__(self, x, y, temp, resistance, capacity, type):
        self.id:int = None
        self.x:int = x
        self.y:int = y
        self.temp:float = temp+random.gauss(0,0.1) # in Kelvin
        self.resistance:float = resistance # in Kelvin/Watt
        self.capacity:float = capacity # in Joules/Kelvin
        self.neighbors:list = []
        self.type:int = type

    def injectHeat(self, joules):
        self.temp += joules / self.capacity

    def exchangeHeat(self, timeStep, sourceTemp, sourceResistance):
        if sourceTemp < self.temp:
            return 0
        joules = (sourceTemp - self.temp) / (sourceResistance + self.resistance) * timeStep
        if self.type == self.cellType.conductor:
            self.injectHeat(joules)
        return joules
    
    def transferHeat(self, timeStep):
        # pick a random order for the neighbors
        order = random.sample(range(len(self.neighbors)), len(self.neighbors))
        for neighbor in order:
            transfer = self.neighbors[neighbor].exchangeHeat(timeStep, self.temp, self.resistance)
            self.injectHeat(-transfer)

    def __dict__(self):
        return {
            "x": self.x,
            "y": self.y,
            "temp": self.temp,
            "resistance": self.resistance,
            "capacity": self.capacity,
            "type": self.type
        }


class room:
    def __init__(self, width, height, timeStep):
        self.width = width # in meters
        self.height = height # in meters
        self.timeStep = timeStep # in seconds

    # def initCells(self,
    #              innerTemp, innerResistance, innerCapacity, 
    #              wallResistance, wallCapacity,
    #              outerTemp, outerResistance, outerCapacity):
    #     for x in range(self.height+4):
    #             for y in range(self.width+4):
    #                 if x == 0 or x == self.height+3 or y == 0 or y == self.width+3:
    #                     self.cells.append(cell(y, x, outerTemp, outerResistance, outerCapacity, cell.cellType.heatSink))
    #                 elif x == 1 or x == self.height+2 or y == 1 or y == self.width+2:
    #                     self.cells.append(cell(y, x, (innerTemp-outerTemp)*(wallResistance/(innerTemp+2*wallResistance)) , wallResistance, wallCapacity, cell.cellType.conductor))
    #                 else:
    #                     self.cells.append(cell(y, x, innerTemp, innerResistance, innerCapacity, cell.cellType.conductor))
    #     for x in range(1,self.width+1): # TODO: debug the neighbors creation
    #         for y in range(1,self.height+1):
    #             selectedCell = self.getCell(x, y)
    #             # if x > 0:
    #             selectedCell.neighbors.append(self.getCell(x-1, y))
    #             # if x < self.height+4:
    #             selectedCell.neighbors.append(self.getCell(x+1, y))
    #             # if y > 0:
    #             selectedCell.neighbors.append(self.getCell(x, y-1))
    #             # if y < self.width+4:
    #             selectedCell.neighbors.append(self.getCell(x, y+1))


    def getCell(self, x, y):
        return self.cells[x + y*(self.width+4)]

    def addHeatSource(self,id, x, y, power, p, i, setpoint, sensor):
        self.heatSourcesIds.append(id)
        self.heatSources.append(self.heater(x, y, self, power, p, i, setpoint, sensor))

    def addSensor(self, id, x, y):
        self.sensorsIds.append(id)
        self.sensors.append(self.thermometer(x, y, self))

    def transferHeat(self):
        # get temperature sorted cells indexs
        sortIndex = np.argsort([cell.temp for cell in self.cells])

        for heatSource in self.heatSources:
            heatSource.update()

        for cell in range(len(self.cells)-1,0,-1):
            selectedCell:cell = self.cells[sortIndex[cell]]
            # self.highlightCellNeighbors(self.cells[sortIndex[cell]].x, self.cells[sortIndex[cell]].y)
            if selectedCell.id in self.heatSourcesIds:
                # get the heat source id
                heatSourceId = self.heatSourcesIds.index(selectedCell.id)
                # get the heat source
                heatSource = self.heatSources[heatSourceId]
                selectedCell.injectHeat(heatSource.power*self.timeStep)
            selectedCell.transferHeat(self.timeStep)

    def getTemp(self, x, y):
        cell = self.getCell(x, y)
        return cell.temp
    
    def getSummedTemp(self):
        return sum([cell.temp*cell.capacity for cell in self.cells])
    
    def getInnerTemp(self):
        total = 0
        for x in range(2, self.width+2):
            for y in range(2, self.height+2):
                total += self.getTemp(x, y)
        return total / (self.width*self.height)
    
    def getTemperatureMap(self):
        temp = []
        for cell in self.cells:
            temp.append(cell.temp)
        # turn temp into 2d array
        temp = [temp[i:i+self.width+4] for i in range(0, len(temp), self.width+4)]
        return temp

    def plotTempMap(self, axis:plt.Axes=None):
        temp = self.getTemperatureMap()
        if axis is None:
            plt.imshow(temp, cmap='hot', interpolation='nearest')
        else:
            axis.imshow(temp, cmap='hot', interpolation='nearest')

    def highlightCellNeighbors(self, x, y):
        selectedCell = self.getCell(x, y)
        trueTemps = [cell.temp for cell in selectedCell.neighbors]
        for neighbor in selectedCell.neighbors:
            neighbor.temp = 100
        self.plotTempMap()
        plt.show()
        for i in range(len(selectedCell.neighbors)):
            selectedCell.neighbors[i].temp = trueTemps[i]

    def drawFeatures(self):
        image = np.zeros((self.width+4, self.height+4, 3))
        for x in range(self.width+4):
            for y in range(self.height+4):
                if self.getCell(x, y).type == cell.cellType.heatSink:
                    image[x, y] = (0, 0, 1)
                elif self.getCell(x, y).type == cell.cellType.conductor:
                    image[x, y] = (0, 1, 0)

        for sensor in self.sensors:
            image[sensor.x, sensor.y] = (1, 1, 0)

        for heatSource in self.heatSources:
            image[heatSource.x, heatSource.y] = (1, 0, 1)

        image = np.flipud(np.rot90(image))
        plt.imshow(image)
        plt.show()

    def toDict(self):
        out = {
            "width": self.width,
            "height": self.height,
            "timeStep": self.timeStep,
            "cells": [cell.__dict__() for cell in self.cells]
        }

    def saveRoom(self, path):
        with open(path, "w") as f:
            pass

def main():
    test = room(10, 10, 1)
    print(test.width)

if __name__ == "__main__":
    main()