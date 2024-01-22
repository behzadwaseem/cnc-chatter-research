###################################################################
# this program was made with the Windows 10/11 file paths in mind #
###################################################################

import os
import pandas as pd
import matplotlib.pyplot as plt

# TODO: add ability to make a picture for each graph
# TODO: improve the algorithm to detect when cuts happen
# TODO: multithread so that the user can see the graph while choosing if the data is good


# this is the ABSOLUTE path of the FOLDER that the program will read from. Place any 15cut csv
# files inside the folder and it will read them (it can handle multiple files). The path should
# look something like c:/Users/rest_of_path
READ_PATH = os.path.join("c:/Users/95791/Downloads/inputValues")

# this is the ABSOLUTE path of the FOLDER that the program will create the split files in
# it should like c:/Users/rest_of_path
WRITE_PATH = "c:/Users/95791/Downloads/outputValues"


# this is the part after /d/ and before /edit# in the actual url
SHEET_ID = "1aSEPSUfnHy27OzyU4448njNlq4DLVYU2zhpW1fhJrA0"

SHEET_NAME_GOOD = "GoodEndMill"
SHEET_NAME_BAD = "BadEndMill"
CUT_DATA_RANGE = "E:S"  # columns e to s (the columns that contain the chatter information)


# do not change this, only change the variables within this string
URL_GOOD = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_GOOD}&range={CUT_DATA_RANGE}"
URL_BAD = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_BAD}&range={CUT_DATA_RANGE}"
SHEET_DATA_GOOD = pd.read_csv(URL_GOOD).iloc[1:]
SHEET_DATA_BAD = pd.read_csv(URL_BAD).iloc[1:]
isCurrentFileGood = None  # will be change initialized once files are being read
curFileNum = -1  # the number at the end of the 15cut file

# for splitting the files
DATA_COLLECTION_RATE_HZ = 200  # data collection rate
SLIDING_MAX_SIZE = 300  # the width of the window used for the max data
SLIDING_MIN_SIZE = 600  # the width of the window used for the min data, must be larger than the max size
MIN_CUT_TIME_SECONDS = 4  # the minimum amount of time that a cut needs to be
MIN_MOVE_TIME_SECONDS = 1  # the minimum amount of time that it takes to move to the next cut
CUT_THRESHOLD_Y = 0.2  # the threshold for determining when a cut starts and ends (m/s^2)
CUT_THRESHOLD_Z = 0.25  # the threshold for determining when a cut starts and ends (m/s^2)


# will be initialized when the splits are calculated
fileSplitIndexes = []  # where to split the current 15cut file


# holds the processed data
csvData = pd.DataFrame()


# processes the data in a way to make file splitting easier
def processDataToSplit():
    global SLIDING_MAX_SIZE, SLIDING_MIN_SIZE

    # we don't use the x-axis due to its unreliable data due to how the sensor is mounted on the CNC
    csvData["centeredY"] = csvData["rawY"] - csvData["rawY"].median()
    csvData["centeredZ"] = csvData["rawZ"] - csvData["rawZ"].median()

    # this is used for graphing
    csvData["absY"] = csvData["centeredY"].abs()
    csvData["absZ"] = csvData["centeredZ"].abs()

    # add columns containing the max value of the absolute data in a sliding window (reduce noise)
    csvData["rollingY"] = csvData["absY"].rolling(SLIDING_MAX_SIZE, 1, center=True).max().rolling(SLIDING_MIN_SIZE, 1, center=True).min()
    csvData["rollingZ"] = csvData["absZ"].rolling(SLIDING_MAX_SIZE, 1, center=True).max().rolling(SLIDING_MIN_SIZE, 1, center=True).min()


# calculates where to split the files based on the max window data
def addFileSplits():
    global MIN_CUT_TIME_SECONDS, MIN_MOVE_TIME_SECONDS, DATA_COLLECTION_RATE_HZ, SLIDING_MIN_SIZE, SLIDING_MAX_SIZE, CUT_THRESHOLD_Z

    # first we process the data
    processDataToSplit()

    minCutLen = MIN_CUT_TIME_SECONDS * DATA_COLLECTION_RATE_HZ
    minMoveLen = MIN_MOVE_TIME_SECONDS * DATA_COLLECTION_RATE_HZ

    writingToFile = False

    # line index is the current line we're reading from data
    curCutLen, curNoCutLen, lastCutIndex, lineIndex = 0, 0, 0, 0
    interval = 50  # how many lines we skip each time
    fileLen = len(csvData["rollingY"])

    while lineIndex < fileLen:
        backIndex = lineIndex - 1
        curY = csvData["rollingY"][lineIndex]
        curZ = csvData["rollingZ"][lineIndex]

        if not writingToFile:
            curNoCutLen += interval

            # if the value is large enough, we may have reached a cut
            if curY > CUT_THRESHOLD_Y and curZ > CUT_THRESHOLD_Z:
                writingToFile = True

                # since we skip lines to make processing faster, we check
                # backwards to find exactly when the threshold was crossed
                while csvData["rollingY"][backIndex] > CUT_THRESHOLD_Y and csvData["rollingZ"][backIndex] > CUT_THRESHOLD_Z:
                    backIndex -= 1
                backIndex += 1

                # if we haven't moved for long enough without cutting
                # it's likely we split in the middle of the cut
                # we just go back to the start of the previous cut and continue cutting
                if curNoCutLen - lineIndex + backIndex < minMoveLen:
                    fileSplitIndexes.append(lastCutIndex)

                # if this is a new cut
                else:
                    fileSplitIndexes.append(backIndex)
                    lastCutIndex = backIndex
                    curCutLen = lineIndex - backIndex
        else:
            curCutLen += interval

            if curY < CUT_THRESHOLD_Y and curZ < CUT_THRESHOLD_Z:
                writingToFile = False

                # since we skip lines to make processing faster, we check
                # backwards to find exactly when the threshold was crossed
                while csvData["rollingY"][backIndex] < CUT_THRESHOLD_Y and csvData["rollingZ"][backIndex] < CUT_THRESHOLD_Z:
                    backIndex -= 1
                backIndex += 1

                # if the cut was long enough and it ended
                if curCutLen - lineIndex + backIndex >= minCutLen:
                    fileSplitIndexes.append(backIndex)
                    curNoCutLen = lineIndex - backIndex

                # if the cut is too short, it is likely not a cut
                else:
                    fileSplitIndexes.pop()
                    curNoCutLen += lineIndex - lastCutIndex
                curCutLen = 0

        lineIndex += interval
    return 0


# drops all columns that are not specified
def keepColumns(columnsToKeep):
    csvData.drop(csvData.columns.difference(columnsToKeep), axis=1, inplace=True)


# creates the new cut files in the WRITE_PATH folder
def splitFile():
    global SHEET_DATA_GOOD, SHEET_DATA_BAD, curFileNum, isCurrentFileGood
    differentCutCount = int(len(fileSplitIndexes) / 2)

    keepColumns(['timeStamp', 'angleX', 'angleY', 'angleZ', 'rawX', 'rawY', 'rawZ'])  # we only want raw sensor data

    # make the two folders for storing the two types of cuts
    if not os.path.exists(WRITE_PATH + "/noChatterCuts"):
        os.makedirs(WRITE_PATH + "/noChatterCuts")
    if not os.path.exists(WRITE_PATH + "/chatterCuts"):
        os.makedirs(WRITE_PATH + "/chatterCuts")

    # split the file
    for i in range(differentCutCount):
        curSubset = csvData[fileSplitIndexes[i * 2]:fileSplitIndexes[i * 2 + 1]]

        if isCurrentFileGood:
            curChatterVal = SHEET_DATA_GOOD[SHEET_DATA_GOOD.columns[i]][curFileNum]
        else:
            curChatterVal = SHEET_DATA_BAD[SHEET_DATA_BAD.columns[i]][curFileNum]

        print(f"{curChatterVal} ", end='')

        fileName = ("good_" if isCurrentFileGood else "bad_") + str(curFileNum) + "_" + str(i+1) + ".csv"
        if curChatterVal == 'y':
            curSubset.to_csv(WRITE_PATH + "/chatterCuts/chatter_" + fileName, index=False)
        elif curChatterVal == 'n':
            curSubset.to_csv(WRITE_PATH + "/noChatterCuts/noChatter_" + fileName, index=False)


# remove split index from the fileSplitIndexes array
def removeSplit(cutNumbers):
    try:
        cutsToRemove = [int(i) for i in cutNumbers.split(" ")]
    except ValueError:
        return -1  # the input is not a number

    if int(len(fileSplitIndexes)/2) - len(cutsToRemove) != 15:
        return -2  # the wrong amount of cuts was specified

    # sort from large to small to avoid shifting indexes
    cutsToRemove.sort(reverse=True)

    hasDuplicateVals = False
    lastVal = -1
    for i in cutsToRemove:
        if lastVal == i:
            print("you have entered cut-" + str(i) + " more than once")
            hasDuplicateVals = True
            continue
        lastVal = i

    if hasDuplicateVals:
        return -3  # cuts were duplicated

    if cutsToRemove[0] > int(len(fileSplitIndexes)/2) or cutsToRemove[len(cutsToRemove)-1] < 1:
        return -4  # a cut outside the range was specified

    for i in cutsToRemove:
        fileSplitIndexes.pop(i*2-1)
        fileSplitIndexes.pop(i*2-2)
    return 0  # successfully completed

def addSplit(splitIndexes):
    try:
        cutsToAdd = [int(i) for i in splitIndexes.split(" ")]
    except ValueError:
        return -1  # the input is not a number

    if int(len(fileSplitIndexes)/2) + len(cutsToAdd) != 15:
        return -2  # the wrong amount of cuts was specified

    # sort from large to small to avoid shifting indexes
    cutsToAdd.sort(reverse=True)

    hasDuplicateVals = False
    lastVal = -1
    for i in cutsToAdd:
        if lastVal == i:
            print("you have entered cut-" + str(i) + " more than once")
            hasDuplicateVals = True
            continue
        lastVal = i

    if hasDuplicateVals:
        return -3  # cuts were duplicated

    if cutsToAdd[0] > 15 or cutsToAdd[len(cutsToAdd)-1] < 1:
        return -4  # a cut outside the range was specified

    print(fileSplitIndexes)
    # fill extra cuts with empty sets which will be skipped when the new files are being created
    for i in cutsToAdd:
        if len(fileSplitIndexes) > i*2-2:
            fileSplitIndexes[i*2-2:i*2-2] = [fileSplitIndexes[i*2-2], fileSplitIndexes[i*2-2]]
        else:
            fileSplitIndexes.append(fileSplitIndexes[len(fileSplitIndexes) - 1])
            fileSplitIndexes.append(fileSplitIndexes[len(fileSplitIndexes) - 1])
    print(fileSplitIndexes)
    return 0  # successfully completed

# reset values when reading in a new file of 15cut data
def resetForNewFile():
    global csvData
    csvData = csvData.iloc[0:0]
    fileSplitIndexes.clear()


def main():
    global csvData, curFileNum, isCurrentFileGood

    shouldCreateNewFiles = input("do you want to create new files? (y/n)") == 'y'
    print(f"creating new files has been set to {shouldCreateNewFiles}")

    for root, dirs, files in os.walk(READ_PATH):
        for file in files:
            if not file.endswith(".csv"): continue

            if shouldCreateNewFiles:
                temp = file.split("_")
                curFileNum = int(temp[len(temp) - 1].split(".")[0])
                isCurrentFileGood = temp[1] == 'good'

            print(input("press enter to see " + file))

            # pyarrow is slightly faster but not required, just delete the second parameter to use default
            csvData = pd.read_csv(READ_PATH + "/" + file, engine="pyarrow")

            # the format for the raw data in the 15cut files is time, angleX, angleY, angleZ, accelX, accelY, accelZ
            csvData.columns.values[0:7] = ["timeStamp", "angleX", "angleY", "angleZ", "rawX", "rawY", "rawZ"]

            addFileSplits()

            csvData[["centeredY", "centeredZ"]].plot()

            plt.axhline(y=0, color="r")  # centerline

            cutCount = int(len(fileSplitIndexes) / 2)

            # show the areas that are considered cuts (highlighted in yellow)
            for i in range(cutCount):
                plt.axvspan(fileSplitIndexes[i*2], fileSplitIndexes[i*2+1], color='y', alpha=0.5, lw=0)

            print(f"there are {cutCount} different cuts in this file")

            # create the new window
            plt.show()

            if not shouldCreateNewFiles:
                resetForNewFile()
                continue

            # user splitting
            if input("save this data? (y/n)") == 'n':
                resetForNewFile()
                continue

            print("you have chosen to use the data")

            if cutCount != 15:
                if cutCount > 15:
                    print("remove extra cuts (make sure 15 cuts remain) cut index starts at 1")
                else:
                    print("please add missing cuts (make sure 15 cuts remain) cut index starts at 1")
                    print("missing cuts must be black on the spreadsheet")

                while True:
                    if cutCount > 15:
                        result = removeSplit(input("type the cut numbers to remove separated by a space (e.g. 1 2 5)"))
                    else:
                        result = addSplit(input("type the cut numbers to add separated by a space (e.g. 1 2 5)"))

                    if result == 0:
                        break
                    elif result == -1:
                        print("you can only enter numbers separated by spaces")
                    elif result == -2:
                        print("you specified the wrong amount of cuts. 15 cuts must remain")
                    elif result == -3:
                        print("you cannot specify the same cut multiple times")
                    elif result == -4:
                        print(f"you specified a cut that was outside of the range 1 to {max(cutCount,15)}")

            splitFile()
            print("splitting completed")
            resetForNewFile()


main()
