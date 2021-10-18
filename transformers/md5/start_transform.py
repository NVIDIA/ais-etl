from aistore.client import Client, Bck

client = Client("http://localhost:31337")

# Initialize transform
with open('md5_pod.yaml', 'r') as f:
    spec = f.read()
    transform_id = client.etl_init(spec=spec)

# Transform objects
for i in range(0, 10):
    object_name = "shard-{}.tar".format(i)
    output = client.transform_object(
        transform_id=transform_id,
        object_name=object_name,
        bck=Bck("shards"),
    )
    print(f"{object_name} -> {output}")
