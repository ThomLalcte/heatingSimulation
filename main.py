from matplotlib import pyplot as plt
import numpy as np, random, matplotlib.animation as animation, json

# set the random seed
random.seed(0)

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
        interactions = [self.id]
        # pick a random order for the neighbors
        order = random.sample(range(len(self.neighbors)), len(self.neighbors))
        for neighbor in order:
            transfer = self.neighbors[neighbor].exchangeHeat(timeStep, self.temp, self.resistance)
            self.injectHeat(-transfer)
            interactions.append([transfer, self.neighbors[neighbor].id])
        return interactions

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
        return self.room.getTemp(self.x, self.y)+random.gauss(0,0.05)

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
        self.plotFigure = None
        self.plotAxis = None

    def initCells(self,
                 innerTemp, innerResistance, innerCapacity, 
                 wallResistance, wallCapacity,
                 outerTemp, outerResistance, outerCapacity):
        id = 0
        for x in range(self.width+4):
                for y in range(self.height+4):
                    if x == 0 or x == self.width+3 or y == 0 or y == self.height+3:
                        self.cells.append(cell(id, x, y, outerTemp, outerResistance, outerCapacity, cell.cellType.heatSink))
                    elif x == 1 or x == self.width+2 or y == 1 or y == self.height+2:
                        self.cells.append(cell(id, x, y, (innerTemp-outerTemp)*(wallResistance/(innerTemp+2*wallResistance)) , wallResistance, wallCapacity, cell.cellType.conductor))
                    else:
                        self.cells.append(cell(id, x, y, innerTemp, innerResistance, innerCapacity, cell.cellType.conductor))
                    id += 1
        for selectedCell in self.cells:
            x = selectedCell.x
            y = selectedCell.y
            if x > 0:
                selectedCell.neighbors.append(self.getCell(x-1, y))
            if x < self.width+3:
                selectedCell.neighbors.append(self.getCell(x+1, y))
            if y > 0:
                selectedCell.neighbors.append(self.getCell(x, y-1))
            if y < self.height+3:
                selectedCell.neighbors.append(self.getCell(x, y+1))
                    
    def getCell(self, x, y):
        return self.cells[x*(self.height+4) + y]

    def addHeatSource(self, id, power, p, i, setpoint, sensor):
        selectedCell = self.cells[id]
        return self.addHeatSourceFromXY(selectedCell.x, selectedCell.y, power, p, i, setpoint, sensor)

    def addHeatSourceFromXY(self, x, y, power, p, i, setpoint, sensor):
        self.heatSourcesIds.append(self.getCell(x,y).id)
        self.heatSources.append(heater(x, y, self, power, p, i, setpoint, sensor))
        return self.heatSources[-1]

    def addSensor(self, id):
        selectedCell = self.cells[id]
        return self.addSensorFromXY(selectedCell.x, selectedCell.y)

    def addSensorFromXY(self, x, y):
        self.sensorsIds.append(self.getCell(x,y).id)
        self.sensors.append(thermometer(x, y, self))
        return self.sensors[-1]

    def transferHeat(self):
        # get temperature sorted cells indexs from hottest to coldest
        sortIndex = np.argsort([cell.temp for cell in self.cells])[::-1]

        for heatSource in self.heatSources:
            heatSource.update()

        for cell in iter(sortIndex):
            selectedCell:cell = self.cells[cell]

            # self.highlightCell(cell)
            # self.highlightCellNeighbors(selectedCell.id)
            # self.plotFigure.show()
            # plt.pause(0.1)
            # self.plotAxis.clear()

            if selectedCell.id in self.heatSourcesIds:
                heatSourceId = self.heatSourcesIds.index(selectedCell.id)
                heatSource = self.heatSources[heatSourceId]
                selectedCell.injectHeat(heatSource.power*self.timeStep)
            heatTransfers = selectedCell.transferHeat(self.timeStep)
            # lines = self.highlightInteraction(heatTransfers)
            # # self.labelCells()
            # self.plotFigure.show()
            # plt.pause(0.1)
            # for line in lines:
            #     line.remove()
            # # self.plotAxis.clear()

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

    def initPlot(self):
        self.plotFigure, self.plotAxis = plt.subplots()
        self.plotAxis.set_title("Temperature Map")
        self.plotAxis.set_xlabel("x")
        self.plotAxis.set_ylabel("y")
        # self.plotAxis.set_xticks(range(self.width+4))
        # self.plotAxis.set_yticks(range(self.height+4))
        # self.plotAxis.grid()
        self.plotTempMap()

    def labelCells(self):
        if self.plotFigure == None:
            self.initPlot()
        for cell in self.cells:
            self.plotAxis.text(cell.x, cell.y, cell.id, ha="center", va="center", color="blue")

    def plotTempMap(self):
        if self.plotFigure == None:
            self.initPlot()
        temp = self.getTemperatureMap()
        # plot the temperature map transposed to match the room orientation
        # self.plotAxis.imshow(temp, cmap='hot', interpolation='nearest')
        self.plotAxis.imshow(temp.T, cmap='hot', interpolation='nearest')

    def highlightCellNeighbors(self, id):
        if self.plotFigure == None:
            self.initPlot()
            self.plotTempMap()
        selectedCell = self.cells[id]
        points = []

        for neighbor in selectedCell.neighbors:
            points.append(self.plotAxis.scatter(neighbor.x, neighbor.y, 10, "red", marker="o"))
        # add the selected cell in the title
        self.plotAxis.set_title(f"Cell {selectedCell.id}")
        return points

    def highlightCellNeighborsFromXY(self, x, y):
        return self.highightCellNeighbors(self.getCell(x,y).id)

    def highlightCell(self, id):
        if self.plotFigure == None:
            self.initPlot()
            self.plotTempMap()
        selectedCell = self.cells[id]
        points = []

        points.append(self.plotAxis.scatter(selectedCell.x, selectedCell.y, 10, "green", marker="o"))
        # add the selected cell in the title
        self.plotAxis.set_title(f"Cell {selectedCell.id}")
        return points

    def highlightCellFromXY(self, x, y):
        return self.highightCell(self.getCell(x,y).id)

    def highlightInteraction(self, interactions):
        if self.plotFigure == None:
            self.initPlot()
        self.plotTempMap()
        
        lines = []

        source = self.cells[interactions[0]]
        for interaction in interactions[1:]:
            # plot an arrow from the energy source to the destination
            destination = self.cells[interaction[1]]
            # determine the polarity of the arrow
            if interaction[0] > 0:
                # plot the arrow with a size proportional to the energy transfered
                scaledTransfer = (np.log10(interaction[0])+2)*0.1
                lines.append(self.plotAxis.arrow(source.x, source.y, destination.x-source.x, destination.y-source.y, head_width=scaledTransfer, head_length=scaledTransfer, fc='orange', ec='orange', linewidth=scaledTransfer*3, length_includes_head=True))
        return lines        

    def drawFeatures(self):
        if self.plotFigure == None:
            self.initPlot()
        for cell in self.cells:
            if cell.type == cell.cellType.heatSink:
                self.plotAxis.scatter(cell.x, cell.y, 100, "blue", marker="s")
            elif cell.type == cell.cellType.conductor:
                self.plotAxis.scatter(cell.x, cell.y, 100, "orange", marker="s")
        for heatSource in self.heatSources:
            self.plotAxis.scatter(heatSource.x, heatSource.y, 50, "red", marker="s")
        for sensor in self.sensors:
            self.plotAxis.scatter(sensor.x, sensor.y, 50, "purple", marker="s")
        
        self.plotFigure.show()
        plt.pause(0.1)

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
    setpoint = 30 # Kelvin
    air = (0.1, airCapacity)

    # setpoints = []
    # steadyStatePowers = []
    # for setpoint in range(0,101,5):

    timeStep = 10 # in seconds
    testroom = room(15, 5, timeStep)
    testroom.initCells(20, *air, 3, 100, 0, *air)

    testSensor = testroom.addSensorFromXY(testroom.width//2+2, 2)
    testroom.addHeatSourceFromXY(testroom.width//2+2, testroom.height//2+2, 1000, 10, 0.01, setpoint, testSensor)
    
    testroom.labelCells()
    testroom.drawFeatures()
    plt.show(block=False)
    plt.pause(0.1)


    # for cell in testroom.cells:
    #     points = testroom.highlightCellNeighbors(cell.id)
    #     plt.pause(0.1)
    #     for point in points:
    #         point.remove()


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
        if i % 10 == 0:
            temperatureMap.append(testroom.getTemperatureMap())


    imFigure, imAxis = plt.subplots()
    image = imAxis.imshow(temperatureMap[0].T, cmap='hot', interpolation='nearest')
    def update(frame):
        image.set_data(temperatureMap[frame].T)
        return image
    ani = animation.FuncAnimation(imFigure, update, frames=range(simulationTime//10), interval=10)

    # averagedPower = round(np.mean(heaterPowerOverTime[-100:]),2)
    # setpoints.append(setpoint)
    # steadyStatePowers.append(averagedPower)
    # print(f"setpoint: {testroom.heatSource.setpoint}K'\tsteady state power: {averagedPower}W")

    # plt.plot(totalJoules)
    timeFigure, timeAxis = plt.subplots()
    timeAxis.plot(5*np.array(range(simulationTime)), temperatureOverTime, label="Room Temperature")
    timeAxis.plot(5*np.array(range(simulationTime)), heaterTemperatureOverTime, label="sensor Temperature")
    timeAxis.legend()
    timeAxisPower = timeAxis.twinx()
    timeAxisPower.plot(5*np.array(range(simulationTime)), heaterPowerOverTime, "--")
    plt.show()

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