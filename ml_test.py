#!/usr/bin/env python2
from sklearn import linear_model
from sklearn import svm


def load_data(filename):
    intensity_rows = []
    change_rows = []
    max_intensity = 0
    peak = 0
    with open(filename, "r") as f:
        f.readline() # skip header
        i = 0
        for line in f:
            vals = line.split(",")
            if len(vals) < 3:
                break
            intensity = int(vals[1])
            intensity_rows.append(intensity)
            change_rows.append(int(vals[2]))
            if intensity > max_intensity:
                max_intensity = intensity
                peak = i
            i += 1

    x_data = []
    y_data = []
    for i in range(0, len(intensity_rows) - 5 + 1):
        x = intensity_rows[i:i+5] + change_rows[i:i+5]  # features
        x_data.append(x)
        y = 1 if (i + 2) == peak else 0
        y_data.append(y)
    return x_data, y_data


def main():
    # read training data and generate features
    files = ("finger_heavy.csv", "finger_light.csv", "stick_heavy.csv", "stick_light.csv")
    x_train = []
    y_train = []
    for filename in files:
        x_data, y_data = load_data(filename)
        x_train.extend(x_data)
        y_train.extend(y_data)

    model = svm.SVC(C=1.0, cache_size=1024, gamma=1, verbose=True)
    # model = svm.SVC(C=1.0, cache_size=1024, kernel="poly", degree=2, verbose=True)
    # model = linear_model.LogisticRegressionCV(Cs=20, solver="liblinear")
    # model = linear_model.RidgeClassifierCV()
    model.fit(x_train, y_train)
    # print model.scores_

    x_test, y_test = load_data("stick_light.csv")
    y_pred = model.predict(x_test)
    print model.score(x_test, y_test)
    for row in zip(x_test, y_test, y_pred):
        print row


if __name__ == "__main__":
    main()


