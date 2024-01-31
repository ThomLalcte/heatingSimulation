from matplotlib import pyplot as plt
import numpy as np, random, matplotlib.animation as animation, json


class cell:

    class cellType:
        heatSink = 1
        conductor = 2

    def __init__(self, id, x, y, temp, resistance, capacity, type):
        self.id:int = id
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

    def toDict(self):
        return {
            "x": self.x,
            "y": self.y,
            "temp": self.temp,
            "resistance": self.resistance,
            "capacity": self.capacity,
            "type": self.type
        }

class thermometer:
    def __init__(self, x, y, room):
        self.x = x
        self.y = y
        self.room = room
        self.temp = None

    def getTemp(self):
        return self.room.getTemp(self.x, self.y)

class heater:
    def __init__(self, x, y, room, power, p, i, setpoint, sensor):
        self.x = x
        self.y = y
        self.room = room
        self.power = power
        self.p = p
        self.i = i
        self.integral = 0
        self.lastError = 0
        self.setpoint = setpoint
        self.sensor = sensor
    
    def update(self):
        error = self.setpoint - self.sensor.getTemp()
        self.integral += error * self.room.timeStep
        self.power = self.p*error + self.i*self.integral
        self.power = min(max(self.power, 0),1000)

class room:
    def __init__(self, width, height, timeStep):
        self.width = width # in meters
        self.height = height # in meters
        self.timeStep = timeStep # in seconds
        self.cells:list[cell] = []
        self.heatSources:list[heater] = []
        self.heatSourcesIds:list[int] = []
        self.sensors:list[thermometer] = []
        self.sensorsIds:list[int] = []
        self.plotFigure, self.plotAxis = plt.subplots()

    def initCells(self,
                 innerTemp, innerResistance, innerCapacity, 
                 wallResistance, wallCapacity,
                 outerTemp, outerResistance, outerCapacity):
        id = 0
        for x in range(self.height+4):
                for y in range(self.width+4):
                    if x == 0 or x == self.height+3 or y == 0 or y == self.width+3:
                        self.cells.append(cell(id, x, y, outerTemp, outerResistance, outerCapacity, cell.cellType.heatSink))
                    elif x == 1 or x == self.height+2 or y == 1 or y == self.width+2:
                        self.cells.append(cell(id, x, y, (innerTemp-outerTemp)*(wallResistance/(innerTemp+2*wallResistance)) , wallResistance, wallCapacity, cell.cellType.conductor))
                    else:
                        self.cells.append(cell(id, x, y, innerTemp, innerResistance, innerCapacity, cell.cellType.conductor))
                    id += 1
        for selectedCell in self.cells:
            x = selectedCell.x
            y = selectedCell.y
            if x > 0:
                selectedCell.neighbors.append(self.getCell(x-1, y))
            if x < self.height+2:
                selectedCell.neighbors.append(self.getCell(x+1, y))
            if y > 0:
                selectedCell.neighbors.append(self.getCell(x, y-1))
            if y < self.width+2:
                selectedCell.neighbors.append(self.getCell(x, y+1))
                    
    def getCell(self, x, y):
        return self.cells[x*(self.width+4) + y]

    def addHeatSource(self,id, x, y, power, p, i, setpoint, sensor):
        self.heatSourcesIds.append(id)
        self.heatSources.append(heater(x, y, self, power, p, i, setpoint, sensor))

    def addSensor(self, id, x, y):
        self.sensorsIds.append(id)
        self.sensors.append(thermometer(x, y, self))

    def transferHeat(self):
        # get temperature sorted cells indexs from hottest to coldest
        sortIndex = np.argsort([cell.temp for cell in self.cells])[::-1]

        for heatSource in self.heatSources:
            heatSource.update()

        for cell in iter(sortIndex):
            selectedCell:cell = self.cells[cell]
            self.highlightCellNeighbors(selectedCell.id)
            self.plotFigure.show()

            plt.pause(1)
            self.plotAxis.clear()

            if selectedCell.id in self.heatSourcesIds:
                heatSourceId = self.heatSourcesIds.index(selectedCell.id)
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
        temp = np.array(temp).reshape(self.width+4, self.height+4)
        return temp

    def plotTempMap(self):
        temp = self.getTemperatureMap()
        self.plotAxis.imshow(temp, cmap='hot', interpolation='nearest')

    def highlightCellNeighbors(self, id):
        selectedCell = self.cells[id]
        self.plotTempMap()
        for neighbor in selectedCell.neighbors:
            self.plotAxis.scatter(neighbor.x, neighbor.y, 10, "red", marker="o")
        # add the selected cell in the title
        self.plotAxis.set_title(f"Cell {selectedCell.id}")

    def highlightCellNeighborsFromXY(self, x, y):
        return self.highightCellNeighbors(self.getCell(x,y).id)

    def highlightCell(self, id):
        selectedCell = self.cells[id]
        trueTemp = selectedCell.temp
        selectedCell.temp = 100
        self.plotTempMap()
        plt.show()
        selectedCell.temp = trueTemp

    def highlightCellFromXY(self, x, y):
        return self.highightCell(self.getCell(x,y).id)

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

def simulate():

    # airCapacity = 20.79*88.08 # Joules/Kelvin
    airCapacity = 200 # Joules/Kelvin
    setpoint = 21 # Kelvin
    air = (0.1, airCapacity)
    # timeFigure, timeAxis = plt.subplots()

    # setpoints = []
    # steadyStatePowers = []
    # for setpoint in range(0,101,5):

    timeStep = 10 # in seconds
    testroom = room(5, 5, timeStep)
    testroom.initCells(
        setpoint, *air,
        3, 100,
        0, *air)
    
    sensorCell = testroom.getCell(testroom.width//2+2, 2)
    testroom.addSensor(sensorCell.id, sensorCell.x, sensorCell.y)
    heaterCell = testroom.getCell(testroom.width//2+2, testroom.height//2+2)
    testroom.addHeatSource(heaterCell.id, heaterCell.x, heaterCell.y, 1000, 30, 0.03, setpoint, testroom.sensors[0])

    # for i in range(5):
    #     testroom.highlightCellNeighbors(2+i, 0)

    # testroom.drawFeatures()

    # totalJoules = []
    temperatureOverTime = []
    heaterTemperatureOverTime = []
    heaterPowerOverTime = []
    temperatureMap = []
    simulationTime = 60*10
    for i in range(simulationTime):
        testroom.transferHeat()
        # totalJoules.append(testroom.getSummedTemp())
        temperatureOverTime.append(testroom.getInnerTemp())
        heaterTemperatureOverTime.append(testroom.heatSources[0].sensor.getTemp())
        heaterPowerOverTime.append(testroom.heatSources[0].power)
        # if i % 10 == 0:
        #     temperatureMap.append(testroom.getTemperatureMap())


    # image = plt.imshow(temperatureMap[0], cmap='hot', interpolation='nearest')
    # def update(frame):
    #     image.set_data(temperatureMap[frame])
    #     return image
    # ani = animation.FuncAnimation(timeFigure, update, frames=range(simulationTime//10), interval=10)
    # plt.show()

    # averagedPower = round(np.mean(heaterPowerOverTime[-100:]),2)
    # setpoints.append(setpoint)
    # steadyStatePowers.append(averagedPower)
    # print(f"setpoint: {testroom.heatSource.setpoint}K'\tsteady state power: {averagedPower}W")

    # plt.plot(totalJoules)
    # plt.plot(5*np.array(range(simulationTime)), temperatureOverTime, label="Room Temperature")
    # plt.plot(5*np.array(range(simulationTime)), heaterTemperatureOverTime, label="sensor Temperature")
    # plt.legend()
    # plt.twinx()
    # plt.plot(5*np.array(range(simulationTime)), heaterPowerOverTime, "--")
    # plt.show()

    # plt.plot(setpoints, steadyStatePowers)
    # plt.xlabel("Setpoint [K]")
    # plt.ylabel("Steady State Power [W]")
    # plt.show()
    
    # with open("data.csv", "w") as f:
    #     f.write("setpoint,steady state power\n")
    #     for i in range(len(setpoints)):
    #         f.write(f"{setpoints[i]};{steadyStatePowers[i]}\n".replace(".",","))

def main():
    simulate()

if __name__ == "__main__":
    main()