from ais_tar2tf import AisClient

client = AisClient(url="http://localhost:31337", bucket="shards")

# Initialize transform
f = open('md5_pod.yaml', 'r')
spec = f.read()
transform_id = client.transform_init(spec=spec)

# Transform objects
for i in range(0, 10):
    object_name = "shard-{}.tar".format(i)
    output = client.transform_object(
        transform_id=transform_id,
        object_name=object_name,
    )
    print(f"{object_name} -> {output}")
