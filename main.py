from matplotlib import pyplot as plt
import numpy as np, random, matplotlib.animation as animation


class room:
    def __init__(self, width, height, timeStep):
        self.width = width # in meters
        self.height = height # in meters
        self.timeStep = timeStep # in seconds
        self.cells = []
        self.heatSource = None
        self.sensor = None

    class thermometer:
        def __init__(self, x, y, room):
            self.x = x
            self.y = y
            self.room = room
            self.temp = None

        def getTemp(self):
            return self.room.getTemp(self.x, self.y)

    class heater:
        def __init__(self, x, y, room, p, i, setpoint, sensor):
            self.x = x
            self.y = y
            self.room = room
            self.power = 0
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

    class cell:

        class cellType:
            heatSource = 0
            heatSink = 1
            conductor = 2

        def __init__(self, x, y, temp, resistance, capacity, type):
            self.x = x
            self.y = y
            self.temp = temp+random.gauss(0,0.1) # in Kelvin
            self.resistance = resistance # in Kelvin/Watt
            self.capacity = capacity # in Joules/Kelvin
            self.neighbors = []
            self.type = type

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
    
    def initCells(self,
                 innerTemp, innerResistance, innerCapacity, 
                 wallResistance, wallCapacity,
                 outerTemp, outerResistance, outerCapacity):
        for x in range(self.width+4):
                for y in range(self.height+4):
                    if x == 0 or x == self.width+4 or y == 0 or y == self.height+4:
                        self.cells.append(self.cell(x, y, outerTemp, outerResistance, outerCapacity, self.cell.cellType.heatSink))
                    elif x == 1 or x == self.width+2 or y == 1 or y == self.height+2:
                        self.cells.append(self.cell(x, y, (innerTemp-outerTemp)*(wallResistance/(innerTemp+2*wallResistance)) , wallResistance, wallCapacity, self.cell.cellType.conductor))
                    elif x == self.width//2+2 and y == self.height//2+2:
                        self.cells.append(self.cell(x, y, innerTemp, innerResistance, innerCapacity, self.cell.cellType.heatSource))
                    else:
                        self.cells.append(self.cell(x, y, innerTemp, innerResistance, innerCapacity, self.cell.cellType.conductor))
        for x in range(self.width+4):
            for y in range(self.height+4):
                selectedCell = self.getCell(x, y)
                if x > 0:
                    selectedCell.neighbors.append(self.getCell(x-1, y))
                if x < self.width+3:
                    selectedCell.neighbors.append(self.getCell(x+1, y))
                if y > 0:
                    selectedCell.neighbors.append(self.getCell(x, y-1))
                if y < self.height+3:
                    selectedCell.neighbors.append(self.getCell(x, y+1))
                    
    def getCell(self, x, y):
        return self.cells[x*(self.width+4) + y]

    def transferHeat(self):
        # get temperature sorted cells indexs
        sortIndex = np.argsort([cell.temp for cell in self.cells])

        self.heatSource.update()

        for cell in range(len(self.cells)-1,0,-1):
            # self.highlightCellNeighbors(self.cells[sortIndex[cell]].x, self.cells[sortIndex[cell]].y)
            if self.cells[sortIndex[cell]].type == self.cell.cellType.heatSource:
                self.cells[sortIndex[cell]].injectHeat(self.heatSource.power*self.timeStep)
            self.cells[sortIndex[cell]].transferHeat(self.timeStep)

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

def main():
    # airCapacity = 20.79*88.08 # Joules/Kelvin
    airCapacity = 200 # Joules/Kelvin
    setpoint = 21 # Kelvin
    air = (0.1, airCapacity)
    timeFigure, timeAxis = plt.subplots()

    # setpoints = []
    # steadyStatePowers = []
    # for setpoint in range(0,101,5):

    timeStep = 10 # in seconds
    testroom = room(5, 7, timeStep)
    testroom.initCells(
        setpoint, *air,
        3, 100,
        0, *air)
    
    testroom.sensor = testroom.thermometer(testroom.width//2+2, 2, testroom)
    testroom.heatSource = testroom.heater(testroom.width//2+2, testroom.height//2+2, testroom, 30, 0.03, setpoint, testroom.sensor)

    heaterSensor = testroom.thermometer(testroom.width//2+2, testroom.height//2+2, testroom)
    # for i in range(5):
    #     testroom.highlightCellNeighbors(2+i, 0)


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
        heaterTemperatureOverTime.append(heaterSensor.getTemp())
        heaterPowerOverTime.append(testroom.heatSource.power)
        if i % 10 == 0:
            temperatureMap.append(testroom.getTemperatureMap())


    image = plt.imshow(temperatureMap[0], cmap='hot', interpolation='nearest')
    def update(frame):
        image.set_data(temperatureMap[frame])
        return image
    ani = animation.FuncAnimation(timeFigure, update, frames=range(simulationTime//10), interval=10)
    plt.show()

    # averagedPower = round(np.mean(heaterPowerOverTime[-100:]),2)
    # setpoints.append(setpoint)
    # steadyStatePowers.append(averagedPower)
    # print(f"setpoint: {testroom.heatSource.setpoint}K'\tsteady state power: {averagedPower}W")

    # plt.plot(totalJoules)
    plt.plot(np.array(range(simulationTime))*5, temperatureOverTime, label="Room Temperature")
    plt.plot(np.array(range(simulationTime))*5, heaterTemperatureOverTime, label="Heater Temperature")
    plt.legend()
    plt.twinx()
    plt.plot(np.array(range(simulationTime))*5, heaterPowerOverTime, "--")
    plt.show()

    # plt.plot(setpoints, steadyStatePowers)
    # plt.xlabel("Setpoint [K]")
    # plt.ylabel("Steady State Power [W]")
    # plt.show()
    
    # with open("data.csv", "w") as f:
    #     f.write("setpoint,steady state power\n")
    #     for i in range(len(setpoints)):
    #         f.write(f"{setpoints[i]};{steadyStatePowers[i]}\n".replace(".",","))

if __name__ == "__main__":
    main()