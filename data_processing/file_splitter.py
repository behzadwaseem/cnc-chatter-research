# TODO: add ability to make a picture for each graph

import os
import pandas as pd
import matplotlib.pyplot as plt

# make sure these are the correct paths (don't change URL)
READ_PATH = os.path.join("c:/Users/95791/Downloads/allValues")  # where the 15cut files are stored
WRITE_PATH = "c:/Users/95791/Downloads/outputValues"  # where the individual cuts will be made
SHEET_ID = "1aSEPSUfnHy27OzyU4448njNlq4DLVYU2zhpW1fhJrA0"  # the part after /d/ and before /edit# in the actual url
SHEET_NAME = "GoodEndMill"  # or "BadEndMill"
CUT_DATA_RANGE = "E:S"  # columns e to s (the columns that contain the chatter information)
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}&range={CUT_DATA_RANGE}"

# for splitting the files
DATA_COLLECTION_RATE_HZ = 200  # data collection rate
SLIDING_WINDOW_SIZE = 50
MIN_CUT_TIME_SECONDS = 4  # the minimum amount of time that a cut needs to be
MIN_MOVE_TIME_SECONDS = 1  # the minimum amount of time that it takes to move to the next cut

shouldCreateNewFiles = input("do you want to split the files? (y/n)") == 'y'

# will be initialized when the splits are calculated
splitBounds = {"upperY": 0.0, "lowerY": 0.0, "upperZ": 0.0, "lowerZ": 0.0}
fileSplitIndexes = []
chatterFileCount = 0  # how many files for chatter we've made
noChatterFileCount = 0  # how many files for no chatter we've made

# holds the processed data
csvData = pd.DataFrame()
curFileNumber = -1  # the current file number that we are reading (will be given a value later)

# calculates where to split the files based on the max window data
def addFileSplits():
    global DATA_COLLECTION_RATE_HZ
    medianY = csvData["maxY"].quantile(0.5)
    tenthY = csvData["maxY"].quantile(0.1)
    medianZ = csvData["maxZ"].quantile(0.5)
    tenthZ = csvData["maxZ"].quantile(0.1)

    upperY = max(medianY / 50 + tenthY, 0.4)
    lowerY = min(max(splitBounds["upperY"] / 1.3, medianY / 60 + tenthY), 0.3)
    upperZ = max(medianZ / 50 + tenthZ, 0.4)
    lowerZ = min(max(splitBounds["upperZ"] / 1.3, medianZ / 60 + tenthZ), 0.3)

    splitBounds["upperY"] = upperY
    splitBounds["lowerY"] = lowerY
    splitBounds["upperZ"] = upperZ
    splitBounds["lowerZ"] = lowerZ

    writingToFile = False
    minCutLen = MIN_CUT_TIME_SECONDS * DATA_COLLECTION_RATE_HZ
    minMoveLen = MIN_MOVE_TIME_SECONDS * DATA_COLLECTION_RATE_HZ
    curCutLen, curNoCutLen, lastCutIndex, lineIndex = 0, 0, 0, 0
    fileLen = len(csvData["maxY"])
    interval = 50  # how many lines we skip each time

    while lineIndex < fileLen:
        backIndex = lineIndex - 1
        if not writingToFile:
            curNoCutLen += interval
            if csvData["maxY"][lineIndex] >= upperY or csvData["maxZ"][lineIndex] >= upperZ:
                writingToFile = True

                # since we only check 1 value every 50 lines, when something changes, we backtrack to find
                # a more accurate value
                while csvData["maxY"][backIndex] >= upperY or csvData["maxZ"][backIndex] >= upperZ:
                    backIndex -= 1
                backIndex += 1

                if curNoCutLen - lineIndex + backIndex < minMoveLen:
                    fileSplitIndexes.append(lastCutIndex)
                else:
                    fileSplitIndexes.append(backIndex)
                    lastCutIndex = backIndex
                    curCutLen = lineIndex - backIndex
        else:
            curCutLen += interval
            if csvData["maxY"][lineIndex] <= lowerY and csvData["maxZ"][lineIndex] <= lowerZ:
                writingToFile = False

                # since we only check 1 value every 50 lines, when something changes, we backtrack to find
                # a more accurate value
                while csvData["maxY"][backIndex] <= lowerY and csvData["maxZ"][backIndex] <= lowerZ:
                    backIndex -= 1
                backIndex += 1

                if curCutLen - lineIndex + backIndex >= minCutLen:
                    fileSplitIndexes.append(backIndex - SLIDING_WINDOW_SIZE)
                else:
                    fileSplitIndexes.pop()

        lineIndex += interval


# creates the new cut files in the WRITE_PATH folder
def splitFile():
    global URL, curFileNumber, chatterFileCount, noChatterFileCount
    differentCutCount = int(len(fileSplitIndexes) / 2)
    print(csvData.columns)
    csvData.drop(csvData.columns[[7, 8, 9, 10]], axis=1, inplace=True)  # we only want raw sensor data

    # get information from the Google sheet
    chatterData = pd.read_csv(URL).iloc[1:]

    # make the two folders for storing the two types of cuts
    if not os.path.exists(WRITE_PATH + "/noChatterCuts"):
        os.makedirs(WRITE_PATH + "/noChatterCuts")
    if not os.path.exists(WRITE_PATH + "/chatterCuts"):
        os.makedirs(WRITE_PATH + "/chatterCuts")

    # split the file
    for i in range(differentCutCount):
        curSubset = csvData[fileSplitIndexes[i * 2]:fileSplitIndexes[i * 2 + 1]]
        curChatterVal = chatterData[chatterData.columns[i]][curFileNumber]
        print(f"{curChatterVal} ", end='')
        if curChatterVal == 'y':
            curSubset.to_csv(WRITE_PATH + "/chatterCuts/splitCut" + str(chatterFileCount) + ".csv", index=False)
            chatterFileCount += 1
        elif curChatterVal == 'n':
            curSubset.to_csv(WRITE_PATH + "/noChatterCuts/splitCut" + str(noChatterFileCount) + ".csv", index=False)
            noChatterFileCount += 1


# remove split index from the fileSplitIndexes array
def removeSplit(cutNumbers):
    cutsToRemove = [int(i) for i in cutNumbers.split(" ")]
    cutsToRemove.sort(reverse=True)
    lastRemovedIndex = -1
    for i in cutsToRemove:
        if lastRemovedIndex == i:
            print("you have entered cut-" + str(i) + " more than once")
            continue
        lastRemovedIndex = i
        fileSplitIndexes.pop(i*2-1)
        fileSplitIndexes.pop(i*2-2)


# reset values when reading in a new file of 15cut data
def resetForNewFile():
    global csvData
    csvData = csvData.iloc[0:0]
    fileSplitIndexes.clear()


def main():
    global csvData, SLIDING_WINDOW_SIZE, curFileNumber

    for root, dirs, files in os.walk(READ_PATH):
        for file in files:
            if not file.endswith(".csv"): continue

            temp = file.split("_")
            curFileNumber = int(temp[len(temp)-1].split(".")[0])

            print(input("press enter to see " + file))

            csvData = pd.read_csv(READ_PATH + "/" + file, engine="pyarrow")  # read the current csv file

            # the format for the raw data in the 15cut files is time, angleX, angleY, angleZ, accelX, accelY, accelZ
            csvData.columns.values[0:7] = ["timeStamp", "angleX", "angleY", "angleZ", "rawX", "rawY", "rawZ"]

            # add columns containing the absolute values of the y and z axis
            # we don't use the x-axis due to its unreliable data due to how the sensor is mounted on the CNC
            csvData["absY"] = (csvData["rawY"] - csvData["rawY"].median()).abs()
            csvData["absZ"] = (csvData["rawZ"] - csvData["rawZ"].median()).abs()

            # add columns containing the max value of the absolute data in a sliding window (reduce noise)
            csvData["maxY"] = csvData["absY"].rolling(SLIDING_WINDOW_SIZE, 1).max()
            csvData["maxZ"] = csvData["absZ"].rolling(SLIDING_WINDOW_SIZE, 1).max()

            # find where to split the files
            addFileSplits()

            csvData[["absY", "absZ"]].plot()

            plt.axhline(y=0, color="r")  # centerline
            plt.axhline(y=splitBounds["lowerY"], color="b")  # lower bounds for file splitting
            plt.axhline(y=splitBounds["upperY"], color="g")  # upper bounds for file splitting
            for fileIndex in fileSplitIndexes:
                plt.axvline(x=fileIndex, color="k")

            plt.show()

            if not shouldCreateNewFiles:
                resetForNewFile()
                continue

            print("there were " + str(int(len(fileSplitIndexes)/2)) + " different cuts in this file")
            if input("use this data? (y/n)") == 'n':
                resetForNewFile()
                continue

            print("you have chosen to use the data")

            if int(len(fileSplitIndexes)/2) != 15:
                print("remove extra cuts (make sure 15 cuts remain) cut index starts at 1")
                removeSplit(input("type the cut numbers to remove separated by a space (e.g. 1 2 5)"))

            splitFile()
            print("splitting completed")
            resetForNewFile()


main()
