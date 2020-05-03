import redis
from django.conf import settings
from .models import Product

# 链接redis
r = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


class Recommender:
    def get_product_key(self, produce_id):
        return 'product:{}:purchased_with'.format(produce_id)

    def products_bought(self, products):
        product_ids = [p.id for p in products]
        for product_id in product_ids:
            for with_id in product_id:
                if product_id != with_id:
                    r.zincrby(self.get_product_key(product_id), with_id, amount=1)

    def suggest_products_for(self, products, max_results=6):
        product_ids = [p.id for p in products]
        # 只有一个商品
        if len(product_ids) == 1:
            suggestions = r.zrange(self.get_product_key(product_ids[0]), 0, -1, desc=True)[:max_results]
        else:
            # 生成临时key
            flat_ids = ''.join([str(id) for id in product_ids])
            tmp_key = 'tmp_{}'.format(flat_ids)
            # 对于多个商品,取所有商品的键名keys列表
            keys=[self.get_product_key(id) for id in product_ids]
            # 合并有序机核到临时键
            r.zunionstore(tmp_key,keys)
            #删除与当前列表内商品相同的键
            r.zrem(tmp_key,*product_ids)
            # 获得排名结果
            suggestions=r.zrange(tmp_key,0,-1,desc=True)[:max_results]
            #删除临时键
            r.delete(tmp_key)
        # 获取关联商品通过相关性推荐
        suggested_products_ids=[int(id) for id in suggestions]
        suggested_products=list(Product.objects.filter(id__in=suggested_products_ids))
        suggested_products.sort(key=lambda x:suggested_products_ids.index(x.id))
        return suggested_products

    def clear_purchases(self):
        for id in Product.objects.values_list('id',flat=True):
            r.delete(self.get_product_key(id))
