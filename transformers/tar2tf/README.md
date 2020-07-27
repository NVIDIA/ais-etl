# Tar2Tf transformer

Tar2Tf transforms TAR and TAR.GZ files to TFRecord format.
Additionally, it accepts optional parameters to apply conversions to TAR records and select subset of keys  from a single TAR record.

## Usage

### Build

```console
$ cd src && go build
```

### Run

#### Run without any conversions and selections, on localhost:80
```console
$ ./tar2tf -l localhost -p 80
```

#### Conversions ans selections

Currently there are 4 available conversions to apply to TAR Record.

To specify conversions and selections, use `--spec` or `--spec-file` argument to `./tar2tf` command.

`--spec` argument accepts conversions and selections specification in form of a string.
`--spec-file` argument accepts conversions and selections in form of path to a file containing specification.

##### Specification format

```json
{
  "conversions": [
    conversionSpec1,
    conversionSpec2,
    ...
  ],
  "selections": [
    selectionSpec1,
    selectionSpec2,
    ...
  ]
}
```

Conversions are applied in the order of occurrence in specification.
If there aren't any selections provided, all keys from TAR records, and relevant values, will be used.

##### Decode Conversion

Decodes PNG or JPEG image into object, allowing to apply further image transformations

```json
{
  "type": "Decode",
  "ext_name": "png"
}
```

##### Rotate Conversion

Rotates an image clockwise, accordingly to specified angle. If `angle == 0`, then random rotation is applied.

```json
{
  "type": "Rotate",
  "ext_name": "png",
  "angle": 90
}
```

##### Resize Conversion

Resizes an image accordingly to specified destination size.

```json
{
  "type": "Resize",
  "ext_name": "png",
  "sizes": [28, 28]
}
```

##### Rename Conversion

Rename multiple keys into the specified key.

```json
{
  "type": "Rename",
  "renames": {
    "img": ["png", "jpeg"],
    "video": ["mp4", "avi"]
  }
}
```

> Command above renames "png" and "jpeg" to "img", and renames "mp4" and "avi" to "video"

##### Selection

Select single key from TAR record

```json
{
  "ext_name": "png"
}

```

#### Run with Decode and Rotate selection

```console
$ echo >spec.json "
{
    "conversions": [
     {
       "type": "Decode",
       "ext_name": "png"
     },
     {
       "type": "Rotate",
       "ext_name": "png"
     }
    ],
    "selections": [
     {
       "ext_name": "png"
     },
     {
       "ext_name": "cls"
     }
    ]
}
"

$ ./tar2tf -l "0.0.0.0" -p 80 -spec-file spec.json
```
