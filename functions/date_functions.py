import pendulum


async def ttl_date_parser(ttl_epoch):
    datetime_obj = pendulum.from_timestamp(ttl_epoch)

    return datetime_obj


def minutes_until_expiry(ttl_datetime):
    ttl_datetime = ttl_datetime.in_timezone("UTC")
    current_datetime = pendulum.now("UTC")
    seconds_difference = ttl_datetime.timestamp() - current_datetime.timestamp()
    minutes_difference = seconds_difference / 60

    return int(minutes_difference)


async def ttl_create_epoch(ttl):
    current_epoch = pendulum.now("UTC").timestamp()
    ttl_epoch = current_epoch + (int(ttl) * 60)

    return int(ttl_epoch)
